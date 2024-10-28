import os
import requests
import subprocess
import json
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
            # Send as a document
            with open("ffprobe_output.txt", "w") as f:
                f.write(ffprobe_output)
            client.send_document(message.chat.id, "ffprobe_output.txt")
            os.remove("ffprobe_output.txt")  # Clean up the file after sending

        else:
            client.send_message(message.chat.id, "Error processing the video link.")
    else:
        client.send_message(message.chat.id, "Please send a valid video URL.")

def run_ffprobe(video_link):
    try:
        # Run ffprobe command excluding subtitle streams
        command = [
            "ffprobe", 
            "-v", "error", 
            "-show_format", 
            "-select_streams", "v:a",  # Only select video and audio streams
            video_link
        ]
        print(f"Running command: {' '.join(command)}")  # Print the command for debugging
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # Return ffprobe output
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"FFprobe error: {e.stderr}")  # Print detailed error output
        return None
    
app.run()
