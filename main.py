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

app = Flask(__name__)
@app.route('/')
def home(): return "Raphael Master System Online!"
def run_flask(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

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

# --- SYSTEM 1: PROGRESS BAR WITH ETA ---
async def progress_bar(current, total, ud_type, message, start):
    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        if speed > 0:
            eta = round((total - current) / speed)
            eta_str = f"{eta}s" if eta < 60 else f"{round(eta/60, 2)}m"
        else: eta_str = "0s"
        
        progress = "[{0}{1}]".format(''.join(["▰" for i in range(math.floor(percentage / 10))]), ''.join(["▱" for i in range(10 - math.floor(percentage / 10))]))
        tmp = (f"**{ud_type} Mode**\n{progress} {round(percentage, 2)}%\n"
               f"🚀 Speed: {round(speed / 1024, 2)} KB/s\n⏳ ETA: {eta_str}")
        try: await message.edit(text=tmp)
        except: pass

# --- SYSTEM 2: DYNAMIC BREAK LOGIC ---
def get_sleep_time(file_path):
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb < 100: return 5
    if size_mb < 500: return 10
    return 20

# --- SYSTEM 3: HANDLERS & CALLBACKS ---
@bot.on_message(filters.command("start") & filters.private)
async def start(c, m):
    shutil.rmtree("downloads", ignore_errors=True)
    gc.collect()
    await m.reply_photo(photo=START_PIC, caption="Hello Rimiru, I am Raphael 🦋\nAnti-Freeze & Dynamic Cleanup Active.", reply_markup=get_main_btns())

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
    elif cb.data == "view_thumbs_btn":
        if db_config["v_thumb"]: await cb.message.reply_photo(db_config["v_thumb"], caption="🎬 Video Thumb")
        if db_config["m_thumb"]: await cb.message.reply_photo(db_config["m_thumb"], caption="📚 Manga Thumb")
    elif cb.data == "dlt_thumb_btn":
        db_config["v_thumb"] = db_config["m_thumb"] = None
        await cb.answer("🗑️ Thumbnails Deleted!", show_alert=True)
    elif cb.data == "set_chnl_btn":
        await cb.message.edit_text("📝 Send Channel ID:", reply_markup=BACK_BTN)
        r = await c.listen(cb.message.chat.id)
        db_config["channel"] = int(r.text); await r.reply_text("✅ Linked!")
    elif cb.data == "set_thumb_btn":
        btns = [[InlineKeyboardButton("🎬 VIDEO", callback_data="st_v"), InlineKeyboardButton("📚 MANGA", callback_data="st_m")]]
        await cb.message.edit_text("Choose type:", reply_markup=InlineKeyboardMarkup(btns))
    elif cb.data.startswith("st_"):
        mode = "v_thumb" if "v" in cb.data else "m_thumb"
        await cb.message.edit_text("🖼️ Send Photo.")
        photo_msg = await c.listen(cb.message.chat.id)
        if photo_msg.photo: db_config[mode] = photo_msg.photo.file_id; await photo_msg.reply_text("✅ Saved!")
    elif "type_" in cb.data:
        f_type = "video" if "type_v_" in cb.data else "manga"
        msg_id = int(cb.data.split("_")[-1])
        await cb.message.edit_text(f"📝 Enter Full {f_type.upper()} Name:")
        name_reply = await c.listen(cb.message.chat.id)
        m = await c.get_messages(cb.message.chat.id, msg_id)
        await process_file(c, m, f_type, name_reply.text.strip())

# --- SYSTEM 4: CORE PROCESSING ---
async def process_file(c, m, f_type, user_name):
    shutil.rmtree("downloads", ignore_errors=True)
    if not os.path.exists("downloads"): os.makedirs("downloads")
    gc.collect()

    file = m.video or m.document
    orig_name = getattr(file, "file_name", "") or "file"
    ext = "." + orig_name.split(".")[-1] if "." in orig_name else (".mp4" if f_type == "video" else ".pdf")
    clean_name = user_name.replace(ext, "")
    
    if f_type == "video":
        final_name = f"downloads/{clean_name} [@TEMPEST_MAIN] [@ANIME_SUPPLIER_X]{ext}"
        thumb_id = db_config["v_thumb"]
        final_caption = f"**{os.path.basename(final_name)}**"
    else:
        final_name = f"downloads/{clean_name} [@TEMPEST_MAIN]{ext}"
        thumb_id = db_config["m_thumb"]
        final_caption = None

    sts = await m.reply_text("📥 **Downloading with ETA...**")
    try:
        path = await asyncio.wait_for(
            m.download(file_name=final_name, progress=progress_bar, progress_args=("Downloading", sts, time.time())),
            timeout=1200
        )
        
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return await sts.edit("❌ Error: Download Failed (Disk Full).")

        duration = getattr(file, "duration", 0)
        local_thumb = await c.download_media(thumb_id) if thumb_id else None

        await sts.edit("📤 **Uploading with ETA...**")
        if f_type == "video":
            await c.send_video(
                db_config["channel"], video=path, thumb=local_thumb, 
                caption=final_caption, file_name=os.path.basename(path), 
                duration=duration, supports_streaming=True,
                progress=progress_bar, progress_args=("Uploading", sts, time.time())
            )
        else:
            await c.send_document(
                db_config["channel"], document=path, thumb=local_thumb, 
                caption=final_caption, file_name=os.path.basename(path),
                progress=progress_bar, progress_args=("Uploading", sts, time.time())
            )
        
        # 🛠️ SMART CLEANUP BREAK
        wait_time = get_sleep_time(path)
        await sts.edit(f"⏳ **Mission Success! Break: {wait_time}s...**")
        
        if os.path.exists(path): os.remove(path)
        shutil.rmtree("downloads", ignore_errors=True)
        gc.collect() 
        await asyncio.sleep(wait_time) 

        await sts.edit("✅ Mission Completed, Rimiru!", reply_markup=get_main_btns())
    except Exception as e:
        shutil.rmtree("downloads", ignore_errors=True)
        gc.collect()
        await m.reply_text(f"❌ Error: {e}")

# --- ADMIN COMMANDS ---
@bot.on_message(filters.command("restart") & filters.user(ADMINS))
async def restart_bot(c, m):
    shutil.rmtree("downloads", ignore_errors=True)
    await m.reply_text("🔄 Rebooting..."); os.execl(sys.executable, sys.executable, *sys.argv)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    bot.start()
    print("Raphael Master System Online, Rimiru! 🦋")
    idle()
