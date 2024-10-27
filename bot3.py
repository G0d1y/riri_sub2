import os
import requests
import json
import time
import json
import asyncio
from aiohttp import ClientSession
import shutil
from pyrogram import Client, filters
with open('config3.json') as config_file:
    config = json.load(config_file)

api_id = int(config['api_id'])
api_hash = config['api_hash']
bot_token = config['bot_token']

app = Client("video_download_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

download_dir = "downloads"
os.makedirs(download_dir, exist_ok=True)

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
                    app.edit_message_text(chat_id, message_id, message_content)
                    previous_message = message_content
                last_update_time = current_time

async def convert_video(input_path, output_path, resolution):
    command = [
        "ffmpeg", "-i", input_path,
        "-vf", f"scale={resolution}", "-preset", "veryfast", "-crf", "23", "-c:a", "copy", output_path
    ]
    process = await asyncio.create_subprocess_exec(*command)
    await process.communicate()

@app.on_message(filters.text & filters.private)
async def handle_video_link(client, message):
    video_link = message.text
    original_video_path = os.path.join(download_dir, "original_540p_video.mp4")
    
    message = await client.send_message(message.chat.id, f"شروع دانلود...")
    download_success = await download_video(video_link, original_video_path , message.chat.id, message)
    if not download_success:
        await message.reply("Failed to download video. Please check the link.")
        return

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        print(f"Created directory: {download_dir}")
    else:
        for filename in os.listdir(download_dir):
            file_path = os.path.join(download_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)
                    print(f"Deleted file: {file_path}")
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    print(f"Deleted directory: {file_path}")
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")

    converted_video_480p = os.path.join(download_dir, "video_480p.mp4")
    converted_video_360p = os.path.join(download_dir, "video_360p.mp4")

    await asyncio.gather(
        convert_video(original_video_path, converted_video_480p, "854:480"),
        convert_video(original_video_path, converted_video_360p, "640:360")
    )

    await client.send_document(chat_id=message.chat.id, documnet=converted_video_480p, caption="Here is your 480p video!")
    await client.send_document(chat_id=message.chat.id, documnet=converted_video_360p, caption="Here is your 360p video!")

    os.remove(original_video_path)
    os.remove(converted_video_480p)
    os.remove(converted_video_360p)

app.run()