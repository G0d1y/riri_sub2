from pyrogram import Client, filters
import cloudconvert
import re
import time
import json

with open('config2.json') as config_file:
    config = json.load(config_file)

api_id = int(config['api_id'])
api_hash = config['api_hash']
bot_token = config['bot_token']
cl_api = config['cl_api']

cloudconvert.configure(api_key=cl_api)
app = Client("video_converter_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

RESOLUTION_MAP = {
    "360": "640x360",
    "480": "854x480"
}

@app.on_message(filters.text)
def handle_conversion_request(client, message):
    text = message.text.strip()
    match = re.match(r'(https?://\S+)\s+(360|480)', text)
    
    if match:
        video_url, resolution = match.groups()
        
        if resolution not in RESOLUTION_MAP:
            message.reply_text("رزولوشن‌های پشتیبانی‌شده: 360 و 480 می‌باشد.")
            return
        
        target_resolution = RESOLUTION_MAP[resolution]
        status_message = message.reply_text("در حال شروع تبدیل ویدیو...")
        
        job = cloudconvert.Job.create(payload={
            "tasks": {
                "import-my-file": {
                    "operation": "import/url",
                    "url": video_url
                },
                "convert-my-file": {
                    "operation": "convert",
                    "input": "import-my-file",
                    "output_format": "mkv",
                    "video_resolution": target_resolution,
                },
                "export-my-file": {
                    "operation": "export/url",
                    "input": "convert-my-file"
                }
            }
        })

        job_id = job['id']
        
        while True:
            job = cloudconvert.Job.wait(id=job_id)
            if job['status'] == 'finished':
                download_url = job['tasks']['export-my-file']['result']['files'][0]['url']
                message.reply_text(f"ویدیو شما به {resolution} تبدیل شد. لینک دانلود: {download_url}")
                break
            time.sleep(5)
            status_message.edit("تبدیل در حال انجام است...")

app.run()
