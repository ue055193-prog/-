import os, re, asyncio, requests, time, math, sys, shutil, gc
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from pyromod import listen
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
API_ID = 33194523
API_HASH = "af9f7980aca75bd51e0e36b94f9758fd"
BOT_TOKEN = "8726598869:AAF-8XIeaGTGD5-U9Gx6CAgtB7rwlKd1Oj4"
ADMINS = [7426624114]
START_PIC = "https://graph.org/file/bdcf6fa5362c2343ba8b3-af29186fa110399ca6.jpg"

db_config = {"channel": None, "v_thumb": None, "m_thumb": None}
task_queue = asyncio.Queue()

app = Flask(__name__)
@app.route('/')
def home(): return "Raphael Master System Online!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# 🛠️ STABILITY FIX: Added sleep_threshold
bot = Client(
    "RaphaelMaster", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    sleep_threshold=120 
)

# --- REUSABLE UI ---
def get_main_btns():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📺 Set Channel", callback_data="set_chnl_btn"), 
         InlineKeyboardButton("🖼️ Set Thumbs", callback_data="set_thumb_btn")],
        [InlineKeyboardButton("👁️ View Thumbs", callback_data="view_thumbs_btn"),
         InlineKeyboardButton("🗑️ Reset Thumbs", callback_data="dlt_thumb_btn")],
        [InlineKeyboardButton("About Me", callback_data="about_btn"), 
         InlineKeyboardButton("Support ↗", url="https://t.me/+Th2jHrC0YTY0NDg1")],
        [InlineKeyboardButton("Updates ↗", url="https://t.me/+8WWAU1eJkyYxMjFl")]
    ])

BACK_BTN = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_start")]])

# --- SYSTEM 1: PROGRESS BAR WITH ETA & QUEUE STATUS ---
async def progress_bar(current, total, ud_type, message, start):
    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        if speed > 0:
            eta = round((total - current) / speed)
            eta_str = f"{eta}s" if eta < 60 else f"{round(eta/60, 2)}m"
        else:
            eta_str = "0s"
        
        q_size = task_queue.qsize()
        q_msg = f"\n📦 **Queue Remaining:** {q_size} files" if q_size > 0 else ""

        progress = "[{0}{1}]".format(''.join(["▰" for i in range(math.floor(percentage / 10))]), ''.join(["▱" for i in range(10 - math.floor(percentage / 10))]))
        tmp = (f"**{ud_type} Mode**\n{progress} {round(percentage, 2)}%\n"
               f"🚀 Speed: {round(speed / 1024, 2)} KB/s\n⏳ ETA: {eta_str}{q_msg}")
        try:
            await message.edit(text=tmp)
        except:
            pass

# --- SYSTEM 2: DYNAMIC BREAK LOGIC ---
def get_sleep_time(file_path):
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb < 100: return 5
    if size_mb < 500: return 10
    return 20

# --- SYSTEM 3: WORKER ENGINE ---
async def worker():
    while True:
        c, m, f_type, user_name, sts = await task_queue.get()
        try:
            await process_file_logic(c, m, f_type, user_name, sts)
        except Exception as e:
            print(f"Worker Error: {e}")
        finally:
            task_queue.task_done()

# --- SYSTEM 4: CORE PROCESSING LOGIC ---
async def process_file_logic(c, m, f_type, user_name, sts):
    shutil.rmtree("downloads", ignore_errors=True)
    os.makedirs("downloads", exist_ok=True)
    gc.collect()

    file = m.video or m.document
    orig_name = getattr(file, "file_name", "") or "file"
    ext = "." + orig_name.split(".")[-1] if "." in orig_name else (".mp4" if f_type == "video" else ".pdf")
    
    clean_name = re.sub(r'[\\/*?:"<>|]', "", user_name).replace("\xa0", " ").strip()
    tag = " [@TEMPEST_MAIN] [@ANIME_SUPPLIER_X]" if f_type == "video" else " [@TEMPEST_MAIN]"
    file_path = os.path.join("downloads", f"{clean_name}{tag}{ext}")

    await sts.edit(f"📥 **Handling Meta & Downloading...**\n(Line Remaining: {task_queue.qsize()})")
    try:
        path = await asyncio.wait_for(
            m.download(file_name=file_path, progress=progress_bar, progress_args=("Downloading", sts, time.time())),
            timeout=1500
        )
        
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return await sts.edit("❌ Error: Download Failed (Disk Full).")

        duration = getattr(file, "duration", 0)
        thumb_id = db_config["v_thumb"] if f_type == "video" else db_config["m_thumb"]
        local_thumb = await c.download_media(thumb_id) if thumb_id else None

        await sts.edit("📤 **Uploading with Metadata...**")
        if f_type == "video":
            await c.send_video(
                db_config["channel"], video=path, thumb=local_thumb, 
                caption=f"**{os.path.basename(path)}**", duration=duration, 
                supports_streaming=True, progress=progress_bar, progress_args=("Uploading", sts, time.time())
            )
        else:
            await c.send_document(
                db_config["channel"], document=path, thumb=local_thumb,
                progress=progress_bar, progress_args=("Uploading", sts, time.time())
            )
        
        # 🛠️ SMART DYNAMIC CLEANUP
        wait_time = get_sleep_time(path)
        await sts.edit(f"⏳ **Upload Done! Dynamic Break: {wait_time}s...**")
        
        if os.path.exists(path): os.remove(path)
        if local_thumb: os.remove(local_thumb)
        shutil.rmtree("downloads", ignore_errors=True)
        gc.collect() 
        await asyncio.sleep(wait_time) 

        await sts.edit(f"✅ Mission Completed!\nNext file starting soon.", reply_markup=get_main_btns())
    except Exception as e:
        await sts.edit(f"❌ Error: {e}")
        shutil.rmtree("downloads", ignore_errors=True)
        gc.collect()

# --- SYSTEM 5: HANDLERS & CALLBACKS ---
@bot.on_message(filters.command("start") & filters.private)
async def start(c, m):
    shutil.rmtree("downloads", ignore_errors=True)
    gc.collect()
    await m.reply_photo(photo=START_PIC, caption="Hello Rimiru, I am Raphael 🦋\nFull 188-Line Master System Active.", reply_markup=get_main_btns())

@bot.on_message(filters.private & (filters.video | filters.document))
async def batch_init(c, m):
    if not db_config["channel"]:
        return await m.reply_text("❌ Pehle `/setchnl` ya menu se channel set karein.")
    btns = [[InlineKeyboardButton("🎬 VIDEO", callback_data=f"type_v_{m.id}"), InlineKeyboardButton("📚 MANGA", callback_data=f"type_m_{m.id}")]]
    await m.reply_text("⚡ Select type for this file, Rimiru:", reply_markup=InlineKeyboardMarkup(btns))

@bot.on_callback_query()
async def cb_handler(c, cb):
    if cb.data == "back_start":
        await cb.message.edit_caption(caption="Hello Rimiru, I am Raphael 🦋", reply_markup=get_main_btns())
    elif cb.data == "set_chnl_btn":
        await cb.message.edit_text("📝 Send Channel ID:", reply_markup=BACK_BTN)
        r = await c.listen(cb.message.chat.id)
        db_config["channel"] = int(r.text); await r.reply_text("✅ Linked!")
    elif "type_" in cb.data:
        f_type = "video" if "type_v_" in cb.data else "manga"
        msg_id = int(cb.data.split("_")[-1])
        await cb.message.edit_text(f"📝 Enter Full {f_type.upper()} Name:")
        name_reply = await c.listen(cb.message.chat.id)
        m = await c.get_messages(cb.message.chat.id, msg_id)
        sts = await name_reply.reply_text(f"⏳ Added to Queue (Pos: #{task_queue.qsize() + 1})")
        await task_queue.put((c, m, f_type, name_reply.text.strip(), sts))
    elif cb.data == "set_thumb_btn":
        btns = [[InlineKeyboardButton("🎬 VIDEO", callback_data="st_v"), InlineKeyboardButton("📚 MANGA", callback_data="st_m")]]
        await cb.message.edit_text("Choose type:", reply_markup=InlineKeyboardMarkup(btns))
    elif cb.data.startswith("st_"):
        mode = "v_thumb" if "v" in cb.data else "m_thumb"
        await cb.message.edit_text("🖼️ Send Photo.")
        p = await c.listen(cb.message.chat.id)
        if p.photo: 
            db_config[mode] = p.photo.file_id
            await p.reply_text("✅ Saved!")

# --- ADMIN COMMANDS ---
@bot.on_message(filters.command("restart") & filters.user(ADMINS))
async def restart_bot(c, m):
    shutil.rmtree("downloads", ignore_errors=True)
    await m.reply_text("🔄 Rebooting..."); os.execl(sys.executable, sys.executable, *sys.argv)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    bot.start()
    loop = asyncio.get_event_loop()
    loop.create_task(worker())
    print("Raphael Full Master Online, Rimiru! 🦋")
    idle()
