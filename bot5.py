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
        
        # Send the filtered ffprobe output back to the user
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