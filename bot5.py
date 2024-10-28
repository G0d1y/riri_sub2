import os
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
            client.send_message(message.chat.id, ffprobe_output)
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

    # Add FORMAT section with only duration
    relevant_lines.append("[FORMAT]")
    for line in lines:
        if line.startswith("duration="):  # Capture the duration line
            relevant_lines.append(line)
    relevant_lines.append("[/FORMAT]")

    # Add stream index and codec details
    relevant_lines.append("index=0")
    for line in lines:
        if line.startswith("codec_name=") or line.startswith("codec_long_name=") or \
           line.startswith("profile=") or line.startswith("codec_type=") or \
           line.startswith("width=") or line.startswith("height="):
            relevant_lines.append(line)

    # Check specifically for title and encoder tags
    title_found, encoded_by_found = False, False
    for line in lines:
        if "TAG:title=" in line and not title_found:  # Capture title
            relevant_lines.append(line)
            title_found = True
        elif "TAG:ENCODED_BY=" in line and not encoded_by_found:  # Capture encoded_by
            relevant_lines.append(line)
            encoded_by_found = True

    # If title or encoder was not found, manually add placeholders
    if not title_found:
        relevant_lines.append("TAG:title=Unknown")
    if not encoded_by_found:
        relevant_lines.append("TAG:ENCODED_BY=Unknown")

    return "\n".join(relevant_lines)

app.run()
