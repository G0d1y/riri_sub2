import os
import requests
import subprocess
import json
import threading
import time
from pysrt import SubRipTime
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

video_tasks = []

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
                remaining_time = (total_size - downloaded) / (speed * 1024 * 1024)  # seconds
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

def add_watermark_20_sec(input_video, watermark_text, output_video, font_file):
    # Step 1: Cut the first 20 seconds
    first_part = "first_20_sec.mp4"
    command_cut_20_sec = [
        'ffmpeg',
        '-i', input_video,
        '-t', '20',  # first 20 seconds
        '-c', 'copy',  # no re-encoding
        first_part
    ]
    subprocess.run(command_cut_20_sec)
    
    # Step 2: Add watermark to the first 20 seconds
    watermarked_first_part = "watermarked_first_20_sec.mp4"
    command_watermark = [
        'ffmpeg',
        '-i', first_part,
        '-vf', f"drawtext=text='{watermark_text}':fontcolor=red:fontsize=24:fontfile={font_file}:x=10:y=10:enable='lte(t,20)'",
        '-c:a', 'copy',  # copy audio without re-encoding
        watermarked_first_part
    ]
    subprocess.run(command_watermark)

    # Step 3: Cut the rest of the video (starting from 20 seconds)
    second_part = "rest_of_video.mp4"
    command_cut_rest = [
        'ffmpeg',
        '-i', input_video,
        '-ss', '20',  # skip first 20 seconds
        '-c', 'copy',  # no re-encoding
        second_part
    ]
    subprocess.run(command_cut_rest)
    
    # Step 4: Concatenate the watermarked first part with the rest of the video
    with open('concat_list.txt', 'w') as f:
        f.write(f"file '{watermarked_first_part}'\n")
        f.write(f"file '{second_part}'\n")
    
    command_concat = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', 'concat_list.txt',
        '-c', 'copy',  # no re-encoding
        output_video
    ]
    subprocess.run(command_concat)

def add_soft_subtitle(video_file, subtitle_file, output_file):
    subprocess.run([
        'ffmpeg', '-i', video_file, '-i', subtitle_file, '-c', 'copy', '-c:s', 'srt', 
        '-metadata:s:s:0', 'title=@RiRiMovies', '-disposition:s:0', 'default', output_file
    ])

def trim_video(input_file, output_file, duration=60):
    subprocess.run([
        'ffmpeg', '-i', input_file, '-t', str(duration), '-c', 'copy', output_file
    ])

def process_video_with_links(video_link, subtitle_link, client, chat_id, output_name):
    output_path = output_name + '.mkv'
    message = client.send_message(chat_id, f"در حال پردازش: {output_path}...")
    message_id = message.id

    downloaded = f'downloaded_{output_path}'
    download_file(video_link, downloaded, chat_id, message_id)
    download_file(subtitle_link, output_name + '_subtitle.srt', chat_id, message_id)

    processing_start_time = time.time()
    
    # Step 1: Add watermark
    watermarked_video_path = f'watermarked_{output_name}.mkv'
    font_path = "Sahel-Bold.ttf"
    watermark_text = "بزرگترین کانال دانلود سریال کره ای\n @RiRiKdrama | ریری کیدراما"
    add_watermark_20_sec(downloaded, watermarked_video_path , watermark_text , font_path)

    # Step 2: Add soft subtitles
    final_output_path = f'final_{output_name}.mkv'
    add_soft_subtitle(watermarked_video_path, output_name + '_subtitle.srt', final_output_path)

    processing_end_time = time.time()
    processing_time = processing_end_time - processing_start_time
    client.send_message(chat_id, f"زمان پردازش: {processing_time:.2f} ثانیه")

    trimmed_output_path = output_name + '_trimmed.mkv'
    trim_video(final_output_path, trimmed_output_path, duration=60)
    client.send_document(chat_id, trimmed_output_path)
    client.send_document(chat_id, final_output_path)
    client.send_message(chat_id, f"پردازش {output_name} کامل شد!")

    # Clean up temporary files
    os.remove(downloaded)
    os.remove(output_name + '_subtitle.srt')
    os.remove(watermarked_video_path)
    os.remove(final_output_path)
    os.remove(trimmed_output_path)

@app.on_message(filters.command("start"))
def start_processing(client, message):
    global video_tasks
    video_tasks = []
    client.send_message(message.chat.id, "لطفاً لینک‌های ویدیو و زیرنویس و نام فایل خروجی را ارسال کنید.\nبه صورت زیر:\nvideo_link | subtitle_link | output_name")

@app.on_message(filters.text)
def collect_links(client, message):
    tasks = message.text.splitlines()
    
    for task in tasks:
        if task.strip():
            video_link, subtitle_link, output_name = task.split(" | ")
            video_tasks.append((video_link.strip(), subtitle_link.strip(), output_name.strip()))
    
    if video_tasks:
        client.send_message(message.chat.id, "لینک‌ها دریافت شد. در حال پردازش...")
        for video_link, subtitle_link, output_name in video_tasks:
            threading.Thread(target=process_video_with_links, args=(video_link, subtitle_link, client, message.chat.id, output_name)).start()

        video_tasks.clear()

app.run()
