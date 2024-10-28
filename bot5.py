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

    # Check if the message is a valid video link
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
        # Run ffprobe command to extract required information
        command = [
            "ffprobe", 
            "-v", "error", 
            "-show_format", 
            "-show_streams", 
            "-select_streams", "v:0",  # Select the first video stream only
            "-of", "ini",  # Output format as ini
            video_link
        ]
        print(f"Running command: {' '.join(command)}")  # Print the command for debugging
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # Parse the output to keep only relevant parts
        output = result.stdout
        formatted_output = format_ffprobe_output(output)

        return formatted_output
    except subprocess.CalledProcessError as e:
        print(f"FFprobe error: {e.stderr}")  # Print detailed error output
        return None

def format_ffprobe_output(output):
    # Split the output into lines and filter relevant information
    lines = output.splitlines()
    relevant_lines = []

    # Add FORMAT section
    relevant_lines.append("[FORMAT]")
    for line in lines:
        if line.startswith("filename=") or line.startswith("nb_streams=") or \
           line.startswith("nb_programs=") or line.startswith("format_name=") or \
           line.startswith("format_long_name=") or line.startswith("start_time=") or \
           line.startswith("duration=") or line.startswith("size=") or \
           line.startswith("bit_rate=") or line.startswith("probe_score=") or \
           line.startswith("TAG:title=") or line.startswith("TAG:ENCODED_BY=") or \
           line.startswith("TAG:ENCODER="):
            relevant_lines.append(line)

    relevant_lines.append("[/FORMAT]")

    # Add stream index
    relevant_lines.append("index=0")
    for line in lines:
        if line.startswith("codec_name=") or line.startswith("codec_long_name=") or \
           line.startswith("profile=") or line.startswith("codec_type=") or \
           line.startswith("codec_time_base=") or line.startswith("codec_tag_string=") or \
           line.startswith("codec_tag=") or line.startswith("width=") or \
           line.startswith("height="):
            relevant_lines.append(line)

    return "\n".join(relevant_lines)

app.run()
