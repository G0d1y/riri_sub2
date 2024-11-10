import os
import queue
import json
import threading
import time
import asyncio
from pyrogram import Client, filters
from downloader import download_file , download_document , cancel_event
from ffmpeg import process_videos , change_fps , get_video_fps, shift_subtitles , add_soft_subtitle , trim_video , get_aac_profile , low_qulity
from urllib.parse import urlparse
import requests
import zipfile
import shutil
with open('config.json') as config_file:
    config = json.load(config_file)

api_id = int(config['api_id'])
api_hash = config['api_hash']
bot_token = config['bot_token']

app = Client(
    "bot",
    api_id=api_id,
    api_hash=api_hash,
    bot_token=bot_token
)
video_queue = queue.Queue()

video_tasks = []
admins = [5429433533 , 6459990242]
user_state = {}

ongoing_downloads = {}

@app.on_message(filters.command("ost"))
def download_and_unzip(client, message):
    if len(message.command) < 2:
        client.send_message(message.chat.id, "لطفاً لینک فایل را وارد کنید.")
        return

    url = message.command[1]
    zip_filename = "downloaded.zip"
    extract_folder = "extracted_files"

    try:
        client.send_message(message.chat.id, "در حال دانلود فایل ZIP...")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(zip_filename, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        if not os.path.exists(zip_filename):
            client.send_message(message.chat.id, "خطا: فایل ZIP دانلود نشد.")
            return
        
        client.send_message(message.chat.id, "فایل ZIP با موفقیت دانلود شد. در حال استخراج فایل‌ها...")

        os.makedirs(extract_folder, exist_ok=True)

        with zipfile.ZipFile(zip_filename, "r") as zip_ref:
            zip_ref.extractall(extract_folder)

        files_sent = 0
        for root, _, files in os.walk(extract_folder):
            for file in files:
                file_path = os.path.join(root, file)
                client.send_document(message.chat.id, file_path)
                files_sent += 1

        if files_sent == 0:
            client.send_message(message.chat.id, "هیچ فایلی برای ارسال یافت نشد.")
        else:
            client.send_message(message.chat.id, f"مجموعاً {files_sent} فایل ارسال شد.")

        os.remove(zip_filename)
        shutil.rmtree(extract_folder)

    except requests.exceptions.RequestException as e:
        client.send_message(message.chat.id, f"خطا در دانلود فایل: {e}")
    except zipfile.BadZipFile:
        client.send_message(message.chat.id, "فایل ZIP معتبر نیست.")
    except Exception as e:
        client.send_message(message.chat.id, f"خطا: {e}")

@app.on_message(filters.command("clear"))
def remove_files(client , message):
    exclude_files = {
    'x264_HE.mkv' , 'x264_LC.mkv' , 'x265_HE.mkv' , 'x265_LC.mkv' ,
    'x264_HE_5.1.mkv' , 'x264_LC_5.1.mkv' , 'x265_HE_5.1.mkv' , 'x265_LC_5.1.mkv'
    }

    directory = os.getcwd()

    for filename in os.listdir(directory):
        if filename.endswith(('.mkv', '.srt', '.mp4')) and filename not in exclude_files:
            file_path = os.path.join(directory, filename)
            print(file_path)
            os.remove(file_path)
    client.send_message(message.chat.id, "فایل های قبلی حذف شدند")

async def process_video_with_files(video_file, subtitle_file, output_name, client, chat_id):
    output_path = output_name + '.mkv'
    full_output = f'full_{output_path}'
    processing_start_time = time.time()
    for output_file in [full_output, output_path, 'trimmed.mkv' , 'trimmed_low_quality.mkv']:
        if os.path.exists(output_file):
            os.remove(output_file)
            print(f"Deleted existing file: {output_file}")
    shifted_subtitle_file = shift_subtitles(subtitle_file, delay_seconds=15, delay_milliseconds=40)
    aac_profile = get_aac_profile(video_file)
    format = ''
    channel = ''
    codec = ''
    if aac_profile == "x264_HE":
        format = "AAC (HE)"
        channel = "‌Stereo"
        codec = "x264"
    if aac_profile == "x264_LC":
        format = "AAC (LC)"
        channel = "‌Stereo"
        codec = "x264"
    if aac_profile == "x265_HE":
        format = "AAC (HE)"
        channel = "‌Stereo"
        codec = "x265"
    if aac_profile == "x265_LC":
        format = "AAC (LC)"
        channel = "‌Stereo"
        codec = "x265"
    if aac_profile == "x264_HE_5.1":
        format = "AAC (HE)"
        channel = "5.1"
        codec = "x264"
    if aac_profile == "x264_LC_5.1":
        format = "AAC (LC)"
        channel = "5.1"
        codec = "x264"
    if aac_profile == "x265_HE_5.1":
        format = "AAC (HE)"
        channel = "5.1"
        codec = "x265"
    if aac_profile == "x265_LC_5.1":
        format = "AAC (LC)"
        channel = "5.1"
        codec = "x265"

    fps = str(get_video_fps(video_file))[:2]
    fps = int(fps)
    if fps == 30:
        aac_profile += '.mkv'
        await client.send_message(chat_id, f"نوع فرمت صدای ویدیو {format} تشخیص داده شد"+ "\n" + f"کدک ویدی {codec} تشخیص داده شد!"+ "\n" + f"چنل صدا {channel} تشخیص داده شد!" + "\n" + f"fps: {fps} ")
        process_videos(video_file, aac_profile, full_output)
    elif fps == 25: 
        aac_profile += '_25.mkv'
        await client.send_message(chat_id, f"نوع فرمت صدای ویدیو {format} تشخیص داده شد"+ "\n" + f"کدک ویدی {codec} تشخیص داده شد!"+ "\n" + f"چنل صدا {channel} تشخیص داده شد!" + "\n" + f"fps: {fps} ")
        process_videos(video_file, aac_profile, full_output)
    else:
        aac_profile += '.mkv'
        await client.send_message(chat_id, f"نوع فرمت صدای ویدیو {format} تشخیص داده شد"+ "\n" + f"کدک ویدی {codec} تشخیص داده شد!"+ "\n" + f"چنل صدا {channel} تشخیص داده شد!" + "\n" + f"FPS ناشناخته تشخیص داده شد! \n FPS: {fps}")
        change_fps(aac_profile , "trailer.mkv" , fps)
        process_videos(video_file, aac_profile, full_output)

    final_output_path = f'{output_name}.mkv'
    add_soft_subtitle(full_output, shifted_subtitle_file, final_output_path)
    
    processing_time = time.time() - processing_start_time
    await client.send_message(chat_id, f"زمان پردازش: {processing_time:.2f} ثانیه")
    await client.send_document(chat_id, final_output_path, thumb="cover.jpg")
    await client.send_message(chat_id, f"پردازش {output_name} کامل شد!")

    os.remove(video_file)
    os.remove(subtitle_file)
    os.remove(shifted_subtitle_file)
    os.remove(final_output_path)
    os.remove(full_output)

@app.on_message(filters.document)
async def handle_document(client, message):
    if message.chat.id not in admins:
        await client.send_message(message.chat.id, "شما دسترسی لازم را ندارید.")
        return

    document = message.document
    if document.mime_type in ["video/x-matroska", "video/mp4"]:
        video_file = await download_document(client, document, "video.mkv" , message.chat.id)
        await client.send_message(message.chat.id, "لطفاً فایل زیرنویس با فرمت SRT را ارسال کنید.")

        user_state[message.chat.id] = {"video_file": video_file, "step": "waiting_for_subtitle"}
        return

    if message.chat.id in user_state and user_state[message.chat.id]["step"] == "waiting_for_subtitle":
        subtitle_file = await download_document(client, document, "subtitle.srt" , message.chat.id)
        video_file = user_state[message.chat.id]["video_file"]
        await client.send_message(message.chat.id, "لطفاً نام خروجی را ارسال کنید.")

        user_state[message.chat.id]["subtitle_file"] = subtitle_file
        user_state[message.chat.id]["step"] = "waiting_for_output_name"
        return
    
@app.on_message(filters.text)
async def handle_output_name(client, message):
    bot_info = await client.get_me()
    bot_id = bot_info.id

    if message.from_user.id == bot_id:
        return

    print("test")
    if message.chat.id not in admins:
        await client.send_message(message.chat.id, "شما دسترسی لازم را ندارید.")
        return
    if message.chat.id in user_state and user_state[message.chat.id]["step"] == "waiting_for_output_name":
        output_name = message.text.strip()
        if output_name:
            original_video_file = user_state[message.chat.id]["video_file"]
            original_subtitle_file = user_state[message.chat.id]["subtitle_file"]

            new_video_file = f"downloaded_{output_name}.mkv" 
            new_subtitle_file = f"{output_name}_subtitle.srt"
            for output_file in [new_video_file, new_subtitle_file, output_name + '_subtitle.srt' , output_name + '_subtitle_shifted.srt']:
                if os.path.exists(output_file):
                    os.remove(output_file)
            print(f"Deleted existing file: {output_file}")
            if os.path.exists(original_video_file):
                os.rename(original_video_file, new_video_file)

            if os.path.exists(original_subtitle_file):
                os.rename(original_subtitle_file, new_subtitle_file)
            print(original_video_file , new_video_file + " <==========>" + original_subtitle_file , new_subtitle_file)
            await process_video_with_files(new_video_file, new_subtitle_file, output_name, client, message.chat.id)

            del user_state[message.chat.id]
        else:
            await client.send_message(message.chat.id, "لطفاً نام خروجی را به درستی وارد کنید.")
    else: 
        tasks = [line.strip() for line in message.text.splitlines() if line.strip()]

        for i in range(0, len(tasks), 3):
            if i + 2 < len(tasks):
                video_link = tasks[i].strip()
                subtitle_link = tasks[i + 1].strip()
                output_name = tasks[i + 2].strip()

                if video_link and subtitle_link and output_name:
                    video_queue.put((video_link, subtitle_link, output_name, client, message.chat.id))

        if not video_queue.empty():
            await client.send_message(message.chat.id, "لینک‌ها دریافت شد. در حال پردازش...")

def get_extension_from_url(url):
    parsed_url = urlparse(url)
    path = parsed_url.path
    _, ext = os.path.splitext(path)
    print(ext)
    return ext

def process_video_with_links(video_link, subtitle_link, client, chat_id, output_name):
    if chat_id not in admins:
        client.send_message(chat_id, "شما دسترسی لازم را ندارید.")
        return

    output_path = output_name + '.mkv'
    full_output =  f'full_{output_path}'
    message = client.send_message(chat_id, f"در حال پردازش: {output_path}...")
    message_id = message.id

    downloaded = f'downloaded_{output_path}'
    for output_file in [downloaded, full_output, output_path , output_name + '_subtitle.srt' , output_name + '_subtitle_shifted.srt' , 'trimmed.mkv' , 'trimmed_low_quality.mkv']:
        if os.path.exists(output_file):
            os.remove(output_file)
            print(f"Deleted existing file: {output_file}")

    asyncio.run(download_file(client, video_link, downloaded, chat_id , message_id))
    ext = get_extension_from_url(subtitle_link)
    asyncio.run(download_file(client, subtitle_link, output_name + '_subtitle' + ext, chat_id , message_id))
    if cancel_event.is_set() == False:
        processing_start_time = time.time()

        shifted_subtitle_file = shift_subtitles(output_name + '_subtitle.srt', delay_seconds=15, delay_milliseconds=40)
    
        aac_profile = get_aac_profile(downloaded)
        if aac_profile == "x264_HE.mkv":
            client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (HE) تشخیص داده شد"+ "\n" + "کدک ویدی x264 تشخیص داده شد!"+ "\n" + "چنل صدا ‌Stereo تشخیص داده شد!")
        if aac_profile == "x264_LC.mkv":
            client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (LC) تشخیص داده شد" + "\n" + "کدک ویدی x264 تشخیص داده شد!"+ "\n" + "چنل صدا ‌Stereo تشخیص داده شد!")
        if aac_profile == "x265_HE.mkv":
            client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (HE) تشخیص داده شد"+ "\n" + "کدک ویدی x265 تشخیص داده شد!"+ "\n" + "چنل صدا ‌Stereo تشخیص داده شد!")
        if aac_profile == "x265_LC.mkv":
            client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (LC) تشخیص داده شد" + "\n" + "کدک ویدی x265 تشخیص داده شد!"+ "\n" + "چنل صدا ‌Stereo تشخیص داده شد!")
        if aac_profile == "x264_HE_5.1.mkv":
            client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (HE) تشخیص داده شد"+ "\n" + "کدک ویدی x264 تشخیص داده شد!"+ "\n" + "چنل صدا 5.1 تشخیص داده شد!")
        if aac_profile == "x264_LC_5.1.mkv":
            client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (LC) تشخیص داده شد" + "\n" + "کدک ویدی x264 تشخیص داده شد!"+ "\n" + "چنل صدا 5.1 تشخیص داده شد!")
        if aac_profile == "x265_HE_5.1.mkv":
            client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (HE) تشخیص داده شد"+ "\n" + "کدک ویدی x265 تشخیص داده شد!"+ "\n" + "چنل صدا 5.1 تشخیص داده شد!")
        if aac_profile == "x265_LC_5.1.mkv":
            client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (LC) تشخیص داده شد" + "\n" + "کدک ویدی x265 تشخیص داده شد!" + "\n" + "چنل صدا 5.1 تشخیص داده شد!")

        process_videos(downloaded, aac_profile, full_output)


        final_output_path = f'{output_name}.mkv'
        add_soft_subtitle(full_output, shifted_subtitle_file, final_output_path)

        processing_end_time = time.time()
        processing_time = processing_end_time - processing_start_time
        client.send_message(chat_id, f"زمان پردازش: {processing_time:.2f} ثانیه")

        final = client.send_document("-1002332192205", final_output_path, thumb="cover.jpg")
        final_url = f"https://t.me/c/2332192205/{final.id}"
        client.send_message(chat_id, "final: \n" + final_url)
        client.send_message(chat_id, f"پردازش {output_name} کامل شد!")

        os.remove(downloaded)
        os.remove(output_name + '_subtitle.srt')
        os.remove(shifted_subtitle_file)
        os.remove(final_output_path)
        os.remove(full_output)
    else:
        cancel_event.clear()
        return None

@app.on_message(filters.command("start"))
def start_processing(client, message):
    global video_tasks
    video_tasks = []
    client.send_message(message.chat.id, "لطفاً لینک‌های ویدیو و زیرنویس و نام فایل خروجی را ارسال کنید.\nبه صورت زیر:\nvideo_link | subtitle_link | output_name")
    directory2 = './'
    extensions_to_delete = ['.srt', '.mkv', '.mp4']
    for filename in os.listdir(directory2):
        if any(filename.endswith(ext) for ext in extensions_to_delete):
            file_path = os.path.join(directory2, filename)
            if os.path.isfile(file_path):
                    os.remove(file_path)

def process_video_queue():
    while True:
        try:
            video_link, subtitle_link, output_name, client, chat_id = video_queue.get(timeout=10)
            process_video_with_links(video_link, subtitle_link, client, chat_id, output_name)
            video_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error in processing video: {e}")
            continue

threading.Thread(target=process_video_queue, daemon=True).start()
  
@app.on_message(filters.photo & filters.private)
async def handle_cover(client, message):
    try:
        cover_image_path = 'cover.jpg'
        
        if os.path.exists(cover_image_path):
            os.remove(cover_image_path)
        
        downloaded_file_path = await message.download()
        os.rename(downloaded_file_path, cover_image_path)
        
        await message.reply("عکس کاور دریافت شد...")
        await client.send_photo("-1002310252740" , message.photo.file_id)
        await client.send_photo("-1002332192205" , message.photo.file_id)
    except Exception as e:
        await message.reply(f"Error handling cover image: {str(e)}")

@app.on_callback_query()
async def handle_callback_query(client, callback_query):
    global cancel_event
    if callback_query.data.startswith("cancel:"):
        cancel_event.set()
        await client.answer_callback_query(callback_query.id, "Download cancelled.")

app.run()