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
    """Concatenate trailer.ts and downloaded.ts into final_output."""
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
    """Process videos to create and concatenate them."""
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

def add_watermark(video_path, output_path):
    print("~~~~~~~~ ADDING TRAILER ~~~~~~~~")
    trailer_path = 'trailer.mkv'
    converted_trailer_path = 'converted_trailer.mkv'
    
    width, height, bit_rate, fps = get_video_info(video_path)
    print(width , height , bit_rate , fps)
    convert_trailer_to_match(trailer_path, converted_trailer_path, width, height, bit_rate, fps)
    
    concat_file_path = 'concat_list.txt'
    
    with open(concat_file_path, 'w') as f:
        f.write(f"file '{converted_trailer_path}'\n")
        f.write(f"file '{video_path}'\n")

    concat_cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file_path,
        '-c', 'copy',
        '-y',
        output_path
    ]
    subprocess.run(concat_cmd)

    for file_path in [concat_file_path, converted_trailer_path]:
        if os.path.exists(file_path):
            os.remove(file_path)
    
    return output_path

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

def trim_video(input_file, output_file , output_file2, duration=90):
    subprocess.run([
        'ffmpeg', '-err_detect', 'ignore_err', '-i', input_file, 
        '-t', str(duration), '-c', 'copy', output_file
    ])
    
    subprocess.run([
        'ffmpeg',
        '-i', output_file,
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', "50",
        output_file2
    ])

def get_video_info(video_file):
    probe = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate,bit_rate', '-of', 'json', video_file],
        capture_output=True,
        text=True
    )
    video_info = json.loads(probe.stdout)
    width = video_info['streams'][0]['width']
    height = video_info['streams'][0]['height']
    bit_rate = int(video_info['streams'][0]['bit_rate'])  # in bits
    fps = eval(video_info['streams'][0]['r_frame_rate'])  # convert '30000/1001' to float
    return width, height, bit_rate, fps

def convert_trailer_to_match(trailer_path, output_path, width, height, bit_rate, fps):
    print(f"Converting trailer to {width}x{height} @ {fps}fps with {bit_rate/1000} kbps")
    
    subprocess.run([
        'ffmpeg', '-i', trailer_path, 
        '-vf', f'scale={width}:{height}',
        '-b:v', f'{bit_rate}',
        '-r', f'{fps}',
        '-c:a', 'copy',
        '-y', output_path
    ])

def process_video_with_links(video_link, subtitle_link, client, chat_id, output_name):
    if chat_id not in admins:
        client.send_message(chat_id, "شما دسترسی لازم را ندارید.")
        return

    output_path = output_name + '.mkv'
    message = client.send_message(chat_id, f"در حال پردازش: {output_path}...")
    message_id = message.id

    downloaded = f'downloaded_{output_path}'
    download_file(video_link, downloaded, chat_id, message_id)
    download_file(subtitle_link, output_name + '_subtitle.srt', chat_id, message_id)

    shifted_subtitle_file = shift_subtitles(output_name + '_subtitle.srt', delay_seconds=15, delay_milliseconds=40)

    processing_start_time = time.time()
    
    full_video_path = f'full_{output_name}.mkv'
    trailer_video = 'trailer.mkv'

    process_videos(downloaded, trailer_video, full_video_path)

    final_output_path = f'{output_name}.mkv'
    add_soft_subtitle(full_video_path, shifted_subtitle_file, final_output_path)

    processing_end_time = time.time()
    processing_time = processing_end_time - processing_start_time
    client.send_message(chat_id, f"زمان پردازش: {processing_time:.2f} ثانیه")

    #trimed
    trimmed_output_path = '_trimmed.mkv'
    trimmed_low_quality_output_path = '_trimmed_low_quality.mkv'
    trim_video(final_output_path, trimmed_output_path , trimmed_low_quality_output_path , duration=90)
    client.send_document(chat_id, trimmed_output_path, caption= output_name + '_trimmed_low_quality.mkv', thumb="cover.jpg")
    client.send_document(chat_id, trimmed_low_quality_output_path, output_name + '_trimmed.mkv', thumb="cover.jpg")
    #trimed

    client.send_document(chat_id, final_output_path, thumb="cover.jpg")
    client.send_message(chat_id, f"پردازش {output_name} کامل شد!")

    os.remove(downloaded)
    os.remove(output_name + '_subtitle.srt')
    os.remove(shifted_subtitle_file)
    os.remove(full_video_path)
    os.remove(final_output_path)
    os.remove(trimmed_output_path)

def remove_files(client , chatId):
    exclude_files = {'trailer.mkv'}

    directory = os.getcwd()

    for filename in os.listdir(directory):
        if filename.endswith(('.mkv', '.srt', '.mp4')) and filename not in exclude_files:
            file_path = os.path.join(directory, filename)
            os.remove(file_path)
    client.send_message(chatId, "فایل های قبلی حذف شدند")


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

@app.on_message(filters.text)
def collect_links(client, message):
    if message.chat.id not in admins:
        client.send_message(message.chat.id, "شما دسترسی لازم را ندارید.")
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
        remove_files(client , message.chat.id)
        client.send_message(message.chat.id, "لینک‌ها دریافت شد. در حال پردازش...")

def process_video_queue():
    while True:
        video_link, subtitle_link, output_name, client, chat_id = video_queue.get()
        process_video_with_links(video_link, subtitle_link, client, chat_id, output_name)
        video_queue.task_done()

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
