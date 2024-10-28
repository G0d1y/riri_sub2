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
    
    # Check if the message is a valid video link (you can improve this validation)
    if video_link.startswith("http://") or video_link.startswith("https://"):
        # Run ffprobe on the video link
        ffprobe_output = run_ffprobe(video_link)
        
        # Send the ffprobe output back to the user
        if ffprobe_output:
            client.send_message(message.chat.id, ffprobe_output)
        else:
            client.send_message(message.chat.id, "Error processing the video link.")
    else:
        client.send_message(message.chat.id, "Please send a valid video URL.")

def run_ffprobe(video_link):
    try:
        # Run ffprobe command
        command = ["ffprobe", "-v", "error", "-show_format", "-show_streams", video_link]
        print(f"Running command: {' '.join(command)}")  # Print the command for debugging
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        # Return ffprobe output
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"FFprobe error: {e.stderr}")  # Print detailed error output
        return None

    
app.run()