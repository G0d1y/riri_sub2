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
with open('config2.json') as config_file:
    config = json.load(config_file)

api_id = int(config['api_id'])
api_hash = config['api_hash']
bot_token = config['bot_token']

app = Client(
    "bot_info",
    api_id=api_id,
    api_hash=api_hash,
    bot_token=bot_token
)

@app.on_message(filters.text)
def handle_video_link(client, message):
    video_link = message.text
    
    # Check if the message is a valid video link
    if video_link.startswith("http://") or video_link.startswith("https://"):
        # Download the video
        filename = "downloaded_video.mp4"  # You can adjust the file extension based on the content type
        download_file(video_link, filename, message.chat.id, message.message_id)
        
        # Run ffprobe on the downloaded video file
        ffprobe_output = run_ffprobe(filename)
        
        # Send the filtered ffprobe output back to the user
        if ffprobe_output:
            client.send_message(message.chat.id, ffprobe_output)
        else:
            client.send_message(message.chat.id, "Error processing the downloaded video.")
        
        # Optionally, delete the downloaded file if you no longer need it
        if os.path.exists(filename):
            os.remove(filename)
    else:
        client.send_message(message.chat.id, "Please send a valid video URL.")

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

def run_ffprobe(video_file):
    try:
        # Run ffprobe command
        command = ["ffprobe", "-v", "error", "-show_format", "-show_streams", video_file]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        # Parse the output to extract relevant information
        return parse_ffprobe_output(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"FFprobe error: {e.stderr}")
        return None

def parse_ffprobe_output(output):
    # Initialize a list to store filtered output lines
    filtered_output = []
    
    # Split the output into lines and filter
    for line in output.splitlines():
        if "Input" in line or "Duration" in line or "bitrate" in line or "Stream" in line:
            filtered_output.append(line.strip())
    
    # Join the filtered lines into a single string
    return '\n'.join(filtered_output)

app.run()