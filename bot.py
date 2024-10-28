import os
import queue
import json
import threading
import time
import asyncio
from pyrogram import Client, filters
from downloader import download_file , download_document , cancel_event
from ffmpeg import process_videos , shift_subtitles , add_soft_subtitle , trim_video , get_aac_profile , low_qulity

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

@app.on_message(filters.command("clear"))
def remove_files(client , message):
    exclude_files = {'x264_HE.mkv' , 'x264_LC.mkv' , 'x265_HE.mkv' , 'x265_LC.mkv'}

    directory = os.getcwd()

    for filename in os.listdir(directory):
        if filename.endswith(('.mkv', '.srt', '.mp4')) and filename not in exclude_files:
            file_path = os.path.join(directory, filename)
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
    if aac_profile == "x264_HE.mkv":
        await client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (HE) تشخیص داده شد"+ "\n" + "کدک ویدی x264 تشخیص داده شد!")
    if aac_profile == "x264_LC.mkv":
        await client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (LC) تشخیص داده شد" + "\n" + "کدک ویدی x264 تشخیص داده شد!")
    if aac_profile == "x265_HE.mkv":
        await client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (HE) تشخیص داده شد"+ "\n" + "کدک ویدی x265 تشخیص داده شد!")
    if aac_profile == "x265_LC.mkv":
        await client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (LC) تشخیص داده شد" + "\n" + "کدک ویدی x265 تشخیص داده شد!")

    process_videos(video_file, aac_profile, full_output)
    final_output_path = f'{output_name}.mkv'
    add_soft_subtitle(full_output, shifted_subtitle_file, final_output_path)
    trimmed_output_path = 'trimmed.mkv'
    trim_video(final_output_path, trimmed_output_path, duration=90)
    
    processing_time = time.time() - processing_start_time
    await client.send_message(chat_id, f"زمان پردازش: {processing_time:.2f} ثانیه")
    await client.send_document(chat_id, trimmed_output_path, caption=f"{output_name}\n{trimmed_output_path}", thumb="cover.jpg")
    await client.send_document(chat_id, final_output_path, thumb="cover.jpg")
    await client.send_message(chat_id, f"پردازش {output_name} کامل شد!")

    os.remove(video_file)
    os.remove(subtitle_file)
    os.remove(shifted_subtitle_file)
    os.remove(final_output_path)
    os.remove(full_output)
    os.remove(trimmed_output_path)

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
    print(message.text)
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
    asyncio.run(download_file(client, subtitle_link, output_name + '_subtitle.srt', chat_id , message_id))
    if cancel_event.is_set() == False:
        processing_start_time = time.time()

        shifted_subtitle_file = shift_subtitles(output_name + '_subtitle.srt', delay_seconds=15, delay_milliseconds=40)
    
        aac_profile = get_aac_profile(downloaded)
        if aac_profile == "x264_HE.mkv":
            client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (HE) تشخیص داده شد"+ "\n" + "کدک ویدی x264 تشخیص داده شد!")
        if aac_profile == "x264_LC.mkv":
            client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (LC) تشخیص داده شد" + "\n" + "کدک ویدی x264 تشخیص داده شد!")
        if aac_profile == "x265_HE.mkv":
            client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (HE) تشخیص داده شد"+ "\n" + "کدک ویدی x265 تشخیص داده شد!")
        if aac_profile == "x265_LC.mkv":
            client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (LC) تشخیص داده شد" + "\n" + "کدک ویدی x265 تشخیص داده شد!")
        process_videos(downloaded, aac_profile, full_output)


        final_output_path = f'{output_name}.mkv'
        add_soft_subtitle(full_output, shifted_subtitle_file, final_output_path)

        processing_end_time = time.time()
        processing_time = processing_end_time - processing_start_time
        client.send_message(chat_id, f"زمان پردازش: {processing_time:.2f} ثانیه")

        trimmed_output_path = 'trimmed.mkv'
        trim_video(final_output_path, trimmed_output_path, duration=90)
        client.send_document(chat_id, trimmed_output_path, caption= output_name, thumb="cover.jpg")

        trimmed_low_output_path = 'trimmed_low_quality.mkv'
        low_qulity(trimmed_output_path, trimmed_low_output_path)
        client.send_document(chat_id, trimmed_low_output_path, caption= output_name, thumb="cover.jpg")

        client.send_document(chat_id, final_output_path, thumb="cover.jpg")
        client.send_message(chat_id, f"پردازش {output_name} کامل شد!")

        os.remove(downloaded)
        os.remove(output_name + '_subtitle.srt')
        os.remove(shifted_subtitle_file)
        os.remove(final_output_path)
        os.remove(full_output)
        os.remove(trimmed_output_path)
        os.remove(trimmed_low_output_path)
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
    except Exception as e:
        await message.reply(f"Error handling cover image: {str(e)}")

@app.on_callback_query()
async def handle_callback_query(client, callback_query):
    global cancel_event
    if callback_query.data.startswith("cancel:"):
        cancel_event.set()
        await client.answer_callback_query(callback_query.id, "Download cancelled.")

app.run()