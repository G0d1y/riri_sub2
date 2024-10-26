import os
import json
import asyncio
from aiohttp import ClientSession
from pyrogram import Client, filters
with open('config3.json') as config_file:
    config = json.load(config_file)

api_id = int(config['api_id'])
api_hash = config['api_hash']
bot_token = config['bot_token']

app = Client("video_download_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

download_dir = "downloads"
os.makedirs(download_dir, exist_ok=True)

async def download_video(video_url, output_path):
    async with ClientSession() as session:
        async with session.get(video_url) as response:
            if response.status == 200:
                with open(output_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(1024):
                        f.write(chunk)
                return True
            else:
                return False

async def convert_video(input_path, output_path, resolution):
    command = [
        "ffmpeg", "-i", input_path,
        "-vf", f"scale={resolution}", "-preset", "veryfast", "-crf", "25", "-c:a", "copy", output_path
    ]
    process = await asyncio.create_subprocess_exec(*command)
    await process.communicate()

@app.on_message(filters.text & filters.private)
async def handle_video_link(client, message):
    video_link = message.text
    original_video_path = os.path.join(download_dir, "original_540p_video.mp4")
    
    await message.reply("Starting video download...")
    download_success = await download_video(video_link, original_video_path)
    if not download_success:
        await message.reply("Failed to download video. Please check the link.")
        return

    await message.reply("Converting to 480p and 360p...")
    converted_video_480p = os.path.join(download_dir, "video_480p.mp4")
    converted_video_360p = os.path.join(download_dir, "video_360p.mp4")

    await asyncio.gather(
        convert_video(original_video_path, converted_video_480p, "854:480"),
        convert_video(original_video_path, converted_video_360p, "640:360")
    )

    await client.send_video(chat_id=message.chat.id, video=converted_video_480p, caption="Here is your 480p video!")
    await client.send_video(chat_id=message.chat.id, video=converted_video_360p, caption="Here is your 360p video!")

    # Cleanup
    os.remove(original_video_path)
    os.remove(converted_video_480p)
    os.remove(converted_video_360p)

app.run()