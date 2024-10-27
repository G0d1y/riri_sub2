import os
import json
import time
import requests
import shutil
import subprocess
from pyrogram import Client, filters

with open('config3.json') as config_file:
    config = json.load(config_file)

api_id = int(config['api_id'])
api_hash = config['api_hash']
bot_token = config['bot_token']

app = Client("video_download_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)


def download_video(url, filename, chat_id, message_id):
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
                    app.edit_message_text(chat_id=chat_id, message_id=message_id, text=message_content)
                    previous_message = message_content
                last_update_time = current_time

def convert_video(input_path, output_path, resolution):
    command = [
        "ffmpeg", "-i", input_path,
        "-vf", f"scale={resolution}", "-preset", "veryfast", "-crf", "23", "-c:a", "copy", output_path
    ]
    subprocess.run(command, check=True)

@app.on_message(filters.text & filters.private)
def handle_video_link(client, message):
    video_link = message.text
    original_video_path = os.path.join("original_540p_video.mkv")
    
    message.reply("Starting video download...")
    msg = message.reply("Downloading video...")
    
    for output_file in ["video_480p.mkv", "video_360p.mkv" , "original_540p_video.mkv"]:
        if os.path.exists(output_file):
            os.remove(output_file)
            print(f"Deleted existing file: {output_file}")

    download_video(video_link, original_video_path, message.chat.id, msg.id)

    converted_video_480p = os.path.join("video_480p.mkv")
    converted_video_360p = os.path.join("video_360p.mkv")


    convert_video(original_video_path, converted_video_480p, "854:480")
    convert_video(original_video_path, converted_video_360p, "640:360")

    client.send_document(chat_id=message.chat.id, document=converted_video_480p, caption="Here is your 480p video!")
    client.send_document(chat_id=message.chat.id, document=converted_video_360p, caption="Here is your 360p video!")

    # Clean up
    os.remove(original_video_path)
    os.remove(converted_video_480p)
    os.remove(converted_video_360p)

app.run()
