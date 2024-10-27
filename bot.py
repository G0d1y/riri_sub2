import os
import queue
import requests
import subprocess
import json
import threading
import time
from pysrt import SubRipTime , SubRipItem
import pysrt
from pyrogram import Client, filters
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

DOWNLOAD_DIRECTORY = "./"

@app.on_message(filters.command("clear"))
def remove_files(client , message):
    exclude_files = {'trailer.mkv'}

    directory = os.getcwd()

    for filename in os.listdir(directory):
        if filename.endswith(('.mkv', '.srt', '.mp4')) and filename not in exclude_files:
            file_path = os.path.join(directory, filename)
            os.remove(file_path)
    client.send_message(message.chat.id, "فایل های قبلی حذف شدند")

async def download_document(client, document, file_name, chat_id):
    file_path = os.path.join(DOWNLOAD_DIRECTORY, file_name) 
    
    total_size = int(document.file_size) if document.file_size else 0
    downloaded = 0
    start_time = time.time()

    progress_message = await client.send_message(chat_id, "دانلود آغاز شد...")

    async def progress(current, total):
        nonlocal downloaded
        downloaded = current
        current_time = time.time()
        elapsed_time = current_time - start_time
        
        if elapsed_time > 0:
            speed = (downloaded / (1024 * 1024)) / elapsed_time
            remaining_time = (total_size - downloaded) / (speed * 1024 * 1024) if speed > 0 else float('inf')
        else:
            speed = 0
            remaining_time = float('inf')

        if int(current / (total / 100)) % 3 == 0:
            message_content = (
                f"دانلود: {downloaded / (1024 * 1024):.2f} MB از {total / (1024 * 1024):.2f} MB\n"
                f"سرعت: {speed:.2f} MB/s\n"
                f"زمان باقی‌مانده: {remaining_time:.2f} ثانیه"
            )
            await client.edit_message_text(progress_message.chat.id, progress_message.id, message_content)
    
    try:
        await client.download_media(document, file_path, progress=progress)
        await client.edit_message_text(progress_message.chat.id, progress_message.id, "دانلود کامل شد!")
        return file_path
    except Exception as e:
        print(f"Error downloading file: {e}")
        return None
    
async def process_video_with_files(video_file, subtitle_file, output_name, client, chat_id):
    output_path = output_name + '.mkv'
    full_output = f'full_{output_path}'
    processing_start_time = time.time()
    
    shifted_subtitle_file = shift_subtitles(subtitle_file, delay_seconds=15, delay_milliseconds=40)
    aac_profile = get_aac_profile(video_file)
    if aac_profile == "trailer.mkv":
        await client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (HE) تشخیص داده شد")
    if aac_profile == "trailer2.mkv":
        await client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (LC) تشخیص داده شد")

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
    if message.chat.id in user_state and user_state[message.chat.id]["step"] == "waiting_for_output_name":
        output_name = message.text.strip()
        if output_name:
            original_video_file = user_state[message.chat.id]["video_file"]
            original_subtitle_file = user_state[message.chat.id]["subtitle_file"]

            new_video_file = f"downloaded_{output_name}.mkv" 
            new_subtitle_file = f"{output_name}_subtitle.srt"

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
        if message.chat.id not in admins:
            await client.send_message(message.chat.id, "شما دسترسی لازم را ندارید.")
            return
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

def download_file(url, filename, chat_id, message_id):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0
    start_time = time.time()
    
    with open(filename, 'wb') as f:
        last_update_time = time.time() 
        previous_message = "" 
        for data in response.iter_content(chunk_size=1024):
            f.write(data)
            downloaded += len(data)
            current_time = time.time()
            elapsed_time = current_time - start_time
            
            if elapsed_time > 0:
                speed = (downloaded / (1024 * 1024)) / elapsed_time
                remaining_time = (total_size - downloaded) / (speed * 1024 * 1024)
            else:
                speed = 0
                remaining_time = float('inf')
            
            if current_time - last_update_time >= 1:
                message_content = (
                    f"دانلود: {downloaded / (1024 * 1024):.2f} MB از {total_size / (1024 * 1024):.2f} MB\n"
                    f"سرعت: {speed:.2f} MB/s\n"
                    f"زمان باقی‌مانده: {remaining_time:.2f} ثانیه"
                )
                
                if message_content != previous_message:
                    app.edit_message_text(chat_id, message_id, message_content)
                    previous_message = message_content
                last_update_time = current_time

def create_ts_file(input_video, output_file):
    """Create .ts file from the input video."""
    if os.path.exists(input_video):
        try:
            cmd = [
                'ffmpeg', '-i', input_video, '-c', 'copy',  # Use copy for both audio and video
                '-f', 'mpegts', output_file
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(result.stderr.decode())  # Log any errors
            if result.returncode != 0:
                print(f"Failed to create {output_file}: {result.stderr.decode()}")
        except Exception as e:
            print(f"Error running FFmpeg for {output_file}: {e}")
    else:
        
        print(f"Error: {input_video} not found.")

def concat_videos(trailer_ts, downloaded_ts, final_output):
    if os.path.exists(downloaded_ts) and os.path.exists(trailer_ts):
        try:
            with open('concat_list.txt', 'w') as f:
                f.write(f"file '{trailer_ts}'\n")
                f.write(f"file '{downloaded_ts}'\n")
            print("Concat list created:")
            print(open('concat_list.txt').read())

            cmd = [
                'ffmpeg', '-f', 'concat', '-safe', '0', '-i', 'concat_list.txt',
                '-c', 'copy' , final_output
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(result.stderr.decode())
            if result.returncode != 0:
                print(f"Failed to concatenate videos: {result.stderr.decode()}")
        except Exception as e:
            print(f"Error concatenating videos: {e}")
    else:
        if not os.path.exists(downloaded_ts):
            print(f"Error: {downloaded_ts} not found.")
        if not os.path.exists(trailer_ts):
            print(f"Error: {trailer_ts} not found.")

def process_videos(downloaded_video, trailer_video, final_output):
    trailer_ts = 'trailer.ts'
    downloaded_ts = 'downloaded.ts'

    create_ts_file(trailer_video, trailer_ts)
    create_ts_file(downloaded_video, downloaded_ts)
    concat_videos(trailer_ts, downloaded_ts, final_output)

    try:
        os.remove(trailer_ts)
        os.remove(downloaded_ts)
        os.remove('concat_list.txt')
        print("Cleanup: Deleted temporary files.")
    except Exception as e:
        print(f"Error during cleanup: {e}")

def get_video_fps(video_path):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,bit_rate,r_frame_rate', '-of', 'json', video_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        video_info = json.loads(result.stdout)

        if 'streams' not in video_info or len(video_info['streams']) == 0:
            raise ValueError(f"Video stream info not found in {video_path}. Please check if the file is a valid video.")
        fps_str = video_info['streams'][0].get('r_frame_rate', '0/1')
        fps = eval(fps_str) if fps_str else 0

        return fps

    except Exception as e:
        print(f"Error getting video info: {e}")
        return None, None, None, None
    
def seconds_to_subrip_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return SubRipTime(hours=hours, minutes=minutes, seconds=secs, milliseconds=milliseconds)

def shift_subtitles(subtitle_file, delay_seconds, delay_milliseconds=0):
    print("~~~~~~~~ SHIFTING SOFTSUB ~~~~~~~~")
    subs = pysrt.open(subtitle_file)
    delay = SubRipTime(seconds=delay_seconds, milliseconds=delay_milliseconds)
    for sub in subs:
        sub.start = sub.start + delay
        sub.end = sub.end + delay
    shifted_subtitle_file = subtitle_file.replace('.srt', '_shifted.srt')
    subs.save(shifted_subtitle_file, encoding='utf-8')
    return shifted_subtitle_file

def add_soft_subtitle(video_file, subtitle_file, output_file):
    print("~~~~~~~~ ADDING SOFTSUB ~~~~~~~~")
    subprocess.run([
        'ffmpeg', '-i', video_file, '-i', subtitle_file, 
        '-c', 'copy', '-c:s', 'srt', '-metadata:s:s:0', 'title=@RiRiMovies', 
        '-disposition:s:0', 'default', output_file
    ])

def trim_video(input_file, output_file, duration=90):
    subprocess.run([
        'ffmpeg', '-err_detect', 'ignore_err', '-i', input_file, 
        '-t', str(duration), '-c', 'copy', output_file
    ])

def get_aac_profile(video_file):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=codec_name,profile', 
             '-of', 'json', video_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        probe = json.loads(result.stdout)
        
        audio_stream = next((stream for stream in probe.get('streams', []) if stream['codec_name'] == 'aac'), None)
        
        if not audio_stream:
            print("No AAC audio stream found.")
            return None

        profile = audio_stream.get('profile', '').lower()
        if 'lc' in profile:
            return "trailer2.mkv"
        elif 'he' in profile:
            return "trailer.mkv"
        else:
            return "trailer2.mkv"

    except Exception as e:
        print("Error:", e)
        return None

def process_video_with_links(video_link, subtitle_link, client, chat_id, output_name):
    if chat_id not in admins:
        client.send_message(chat_id, "شما دسترسی لازم را ندارید.")
        return

    output_path = output_name + '.mkv'
    full_output =  f'full_{output_path}'
    message = client.send_message(chat_id, f"در حال پردازش: {output_path}...")
    message_id = message.id

    downloaded = f'downloaded_{output_path}'
    download_file(video_link, downloaded, chat_id, message_id)
    download_file(subtitle_link, output_name + '_subtitle.srt', chat_id, message_id)
    processing_start_time = time.time()

    shifted_subtitle_file = shift_subtitles(output_name + '_subtitle.srt', delay_seconds=15, delay_milliseconds=40)
    
    aac_profile = get_aac_profile(downloaded)
    if aac_profile == "trailer.mkv":
        client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (HE) تشخیص داده شد")
    if aac_profile == "trailer2.mkv":
        client.send_message(chat_id, f"نوع فرمت صدای ویدیو AAC (LC) تشخیص داده شد")
    process_videos(downloaded, aac_profile, full_output)


    final_output_path = f'{output_name}.mkv'
    add_soft_subtitle(full_output, shifted_subtitle_file, final_output_path)

    processing_end_time = time.time()
    processing_time = processing_end_time - processing_start_time
    client.send_message(chat_id, f"زمان پردازش: {processing_time:.2f} ثانیه")

    trimmed_output_path = 'trimmed.mkv'
    trim_video(final_output_path, trimmed_output_path, duration=90)
    client.send_document(chat_id, trimmed_output_path, caption= output_name + "\n" + trimmed_output_path, thumb="cover.jpg")

    client.send_document(chat_id, final_output_path, thumb="cover.jpg")
    client.send_message(chat_id, f"پردازش {output_name} کامل شد!")

    os.remove(downloaded)
    os.remove(output_name + '_subtitle.srt')
    os.remove(shifted_subtitle_file)
    os.remove(final_output_path)
    os.remove(full_output)
    os.remove(trimmed_output_path)

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

app.run()