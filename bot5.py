import subprocess
from pyrogram import Client, filters
import json

# Load configuration
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

# Function to run ffprobe and save output to a file
def save_ffprobe_output(video_url, output_filename):
    try:
        command = ["ffprobe", "-v", "error", "-show_format", "-show_streams", video_url]
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
        
        return output_filename
    except subprocess.CalledProcessError as e:
        print(f"FFprobe error: {e.stderr}")
        return None

# Handler to process video link and send ffprobe output
@app.on_message(filters.text)
def handle_video_link(client, message):
    video_link = message.text
    if video_link.startswith("http://") or video_link.startswith("https://"):
        output_filename = "ffprobe_output.txt"
        file_path = save_ffprobe_output(video_link, output_filename)

        if file_path:
            client.send_document(message.chat.id, file_path)
        else:
            client.send_message(message.chat.id, "Error processing the video link.")
    else:
        client.send_message(message.chat.id, "Please send a valid video URL.")

app.run()
