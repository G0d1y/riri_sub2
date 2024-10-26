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
with open('config3.json') as config_file:
    config = json.load(config_file)

api_id = int(config['api_id'])
api_hash = config['api_hash']
bot_token = config['bot_token']

app = Client("video_download_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

download_dir = "downloads"
os.makedirs(download_dir, exist_ok=True)

@app.on_message(filters.text & filters.private)
async def handle_video_link(client, message):
    video_link = message.text
    original_video_path = os.path.join(download_dir, "original_540p_video.mp4")
    
    try:
        response = requests.get(video_link, stream=True)
        if response.status_code == 200:
            with open(original_video_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
            await message.reply("Video downloaded successfully! Converting to 480p and 360p...")
        else:
            await message.reply("Failed to download video. Please check the link.")
            return
    except Exception as e:
        await message.reply(f"An error occurred while downloading the video: {e}")
        return

    converted_video_480p = os.path.join(download_dir, "video_480p.mp4")
    converted_video_360p = os.path.join(download_dir, "video_360p.mp4")

    ffmpeg_command_480p = [
        "ffmpeg", "-i", original_video_path,
        "-vf", "scale=854:480", "-c:a", "copy", converted_video_480p
    ]
    ffmpeg_command_360p = [
        "ffmpeg", "-i", original_video_path,
        "-vf", "scale=640:360", "-c:a", "copy", converted_video_360p
    ]

    try:
        subprocess.run(ffmpeg_command_480p, check=True)
        subprocess.run(ffmpeg_command_360p, check=True)
    except subprocess.CalledProcessError as e:
        await message.reply(f"An error occurred during video conversion: {e}")
        return

    try:
        await client.send_video(chat_id=message.chat.id, video=converted_video_480p, caption="Here is your 480p video!")
        await client.send_video(chat_id=message.chat.id, video=converted_video_360p, caption="Here is your 360p video!")
    except Exception as e:
        await message.reply(f"An error occurred while sending videos: {e}")
    finally:
        os.remove(original_video_path)
        os.remove(converted_video_480p)
        os.remove(converted_video_360p)

app.run()