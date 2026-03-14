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

bot = Client("RaphaelMaster", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, sleep_threshold=60)

# --- SYSTEM: PROGRESS BAR WITH ETA ---
async def progress_bar(current, total, ud_type, message, start):
    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        elapsed_time = round(diff)
        if speed > 0:
            eta = round((total - current) / speed)
            eta_str = f"{eta}s" if eta < 60 else f"{round(eta/60, 2)}m"
        else: eta_str = "0s"
        
        progress = "[{0}{1}]".format(''.join(["▰" for i in range(math.floor(percentage / 10))]), ''.join(["▱" for i in range(10 - math.floor(percentage / 10))]))
        
        tmp = (f"**{ud_type} Mode**\n"
               f"{progress} {round(percentage, 2)}%\n"
               f"🚀 Speed: {round(speed / 1024, 2)} KB/s\n"
               f"⏳ ETA: {eta_str}")
        try: await message.edit(text=tmp)
        except: pass

# --- SYSTEM: DYNAMIC SLEEP LOGIC ---
def get_sleep_time(file_path):
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb < 100: return 3
    if size_mb < 500: return 7
    if size_mb < 1000: return 12
    return 20 # 1GB+ ke liye 20s break

# --- SYSTEM 3: MASTER PROCESSING ---
async def process_file(c, m, f_type, user_name):
    shutil.rmtree("downloads", ignore_errors=True)
    if not os.path.exists("downloads"): os.makedirs("downloads")
    gc.collect()

    file = m.video or m.document
    orig_name = getattr(file, "file_name", "") or "file"
    ext = "." + orig_name.split(".")[-1] if "." in orig_name else (".mp4" if f_type == "video" else ".pdf")
    
    final_name = f"downloads/{user_name} [@TEMPEST_MAIN]{ext}"
    if f_type == "video":
        final_name = f"downloads/{user_name} [@TEMPEST_MAIN] [@ANIME_SUPPLIER_X]{ext}"

    sts = await m.reply_text("📥 **Initializing Download...**")
    try:
        path = await asyncio.wait_for(
            m.download(file_name=final_name, progress=progress_bar, progress_args=("Downloading", sts, time.time())),
            timeout=1800
        )
        
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return await sts.edit("❌ Error: Download Failed.")

        duration = getattr(file, "duration", 0)
        thumb_id = db_config["v_thumb"] if f_type == "video" else db_config["m_thumb"]
        local_thumb = await c.download_media(thumb_id) if thumb_id else None

        await sts.edit("📤 **Uploading with ETA...**")
        if f_type == "video":
            await c.send_video(db_config["channel"], video=path, thumb=local_thumb, caption=f"**{os.path.basename(path)}**", duration=duration, supports_streaming=True, progress=progress_bar, progress_args=("Uploading", sts, time.time()))
        else:
            await c.send_document(db_config["channel"], document=path, thumb=local_thumb, caption=None, progress=progress_bar, progress_args=("Uploading", sts, time.time()))
        
        # 🛠️ DYNAMIC CLEANUP BREAK
        wait_time = get_sleep_time(path)
        await sts.edit(f"⏳ **Upload Done! Dynamic Break: {wait_time}s for Cleanup...**")
        
        if os.path.exists(path): os.remove(path)
        shutil.rmtree("downloads", ignore_errors=True)
        if local_thumb: os.remove(local_thumb)
        gc.collect() 
        await asyncio.sleep(wait_time) 

        await sts.edit("✅ Mission Completed, Rimiru!", reply_markup=get_main_btns())

    except Exception as e:
        shutil.rmtree("downloads", ignore_errors=True)
        gc.collect()
        await m.reply_text(f"❌ Error: {e}")

# ... (Start, Buttons aur Baaki Handlers same rahenge) ...

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    bot.start()
    idle()
