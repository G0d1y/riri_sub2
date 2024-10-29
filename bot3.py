import os
import json
import time
import requests
import subprocess
import re
import zipfile
from pyrogram import Client, filters

with open('config2.json') as config_file:
    config = json.load(config_file)

api_id = int(config['api_id'])
api_hash = config['api_hash']
bot_token = config['bot_token']

app = Client("video_download_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

def download_video(url, filename, chat_id, message_id):
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
                    app.edit_message_text(chat_id=chat_id, message_id=message_id, text=message_content)
                    previous_message = message_content
                last_update_time = current_time

def download_file(url, filename):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0

    with open(filename, 'wb') as f:
        for data in response.iter_content(chunk_size=1024):
            f.write(data)
            downloaded += len(data)

def unzip_file(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def parse_ffmpeg_output(output_line):
    progress_pattern = re.compile(
        r'frame=\s*(\d+)\s+fps=\s*([\d\.]+)\s+q=\s*([\d\.]+)\s+size=\s*([\d\.]+)KiB\s+'
        r'time=([\d\:\.]+)\s+bitrate=\s*([\d\.]+)kbits/s\s+speed=\s*([\d\.]+)x'
    )
    
    match = progress_pattern.search(output_line)
    if match:
        frame, fps, q, size, current_time, bitrate, speed = match.groups()

        message_content = (
            f"Processing video:\n"
            f"Frame: {frame}\n"
            f"FPS: {fps}\n"
            f"Quality: {q}\n"
            f"Size: {size} KiB\n"
            f"Time: {current_time}\n"
            f"Bitrate: {bitrate} kbits/s\n"
            f"Speed: {speed}x"
        )
        
        return message_content
    return None

def convert_video(input_path, output_path, resolution, chat_id, message_id):
    command = [
        "ffmpeg", "-i", input_path,
        "-vf", f"scale={resolution}", "-preset", "veryfast", "-crf", "23", "-c:a", "copy", output_path
    ]
    last_update_time = time.time()
    previous_message = ""
    process = subprocess.Popen(command, stderr=subprocess.PIPE, universal_newlines=True)

    while True:
        output = process.stderr.readline()
        if output == '' and process.poll() is not None:
            break
        
        if output:
            message_content = parse_ffmpeg_output(output.strip())
            if message_content:
                current_time = time.time()
                if current_time - last_update_time >= 1:  
                    if message_content != previous_message:
                        app.edit_message_text(chat_id=chat_id, message_id=message_id, text=message_content)
                        previous_message = message_content
                        last_update_time = current_time

    process.wait()

@app.on_message(filters.text & filters.private)
def handle_video_link(client, message):
    link = message.text.strip()  # Remove any leading/trailing whitespace
    original_video_path = os.path.join("original_540p_video.mkv")

    # Check if the link has a valid format
    if any(link.endswith(ext) for ext in ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv')):
        msg = message.reply("درحال دانلود ویدیو...")
        download_video(link, original_video_path, message.chat.id, msg.id)
        converted_video_480p = os.path.join("video_480p.mkv")
        convert_msg = message.reply("درحال پردازش ویدیو...")
        convert_video(original_video_path, converted_video_480p, "854:480", message.chat.id, convert_msg.id)
        client.send_document(chat_id=message.chat.id, document=converted_video_480p, caption="Here is your 480p video!")

        # Clean up
        os.remove(original_video_path)
        os.remove(converted_video_480p)

    elif '.zip' in link:  # Check if '.zip' is present anywhere in the link
        msg = message.reply("درحال دانلود فایل ZIP...")
        zip_file_path = "downloaded_file.zip"
        extract_folder = "extracted_files"

        # Download the zip file
        download_file(link, zip_file_path)

        # Create a directory to extract the files
        os.makedirs(extract_folder, exist_ok=True)

        # Unzip the file
        unzip_file(zip_file_path, extract_folder)

        # Send the extracted files back to the user
        for root, dirs, files in os.walk(extract_folder):
            for file in files:
                file_path = os.path.join(root, file)
                client.send_document(chat_id=message.chat.id, document=file_path)

        # Clean up
        os.remove(zip_file_path)
        for file in os.listdir(extract_folder):
            os.remove(os.path.join(extract_folder, file))
        os.rmdir(extract_folder)

    else:
        # If no recognizable format is found, ask the user for input
        msg = message.reply("لینک شما هیچ فرمت قابل شناسایی ندارد. آیا این لینک مربوط به ویدیو است (نوع 1) یا فایل ZIP (نوع 2)؟")

        # Create a new handler for the user's response
        @app.on_message(filters.text & filters.private)
        def handle_user_response(client, user_response):
            if user_response.chat.id == message.chat.id:  # Ensure it matches the original message's chat
                if user_response.text.strip() == "1":
                    # User confirmed it's a video
                    msg.edit("در حال دانلود ویدیو...")
                    download_video(link, original_video_path, message.chat.id, msg.id)
                    converted_video_480p = os.path.join("video_480p.mkv")
                    convert_msg = message.reply("درحال پردازش ویدیو...")
                    convert_video(original_video_path, converted_video_480p, "854:480", message.chat.id, convert_msg.id)
                    client.send_document(chat_id=message.chat.id, document=converted_video_480p, caption="Here is your 480p video!")

                    # Clean up
                    os.remove(original_video_path)
                    os.remove(converted_video_480p)
                elif user_response.text.strip() == "2":
                    # User confirmed it's a zip file
                    msg.edit("درحال دانلود فایل ZIP...")
                    zip_file_path = "downloaded_file.zip"
                    extract_folder = "extracted_files"

                    # Download the zip file
                    download_file(link, zip_file_path)

                    # Create a directory to extract the files
                    os.makedirs(extract_folder, exist_ok=True)

                    # Unzip the file
                    unzip_file(zip_file_path, extract_folder)

                    # Send the extracted files back to the user
                    for root, dirs, files in os.walk(extract_folder):
                        for file in files:
                            file_path = os.path.join(root, file)
                            client.send_document(chat_id=message.chat.id, document=file_path)

                    # Clean up
                    os.remove(zip_file_path)
                    for file in os.listdir(extract_folder):
                        os.remove(os.path.join(extract_folder, file))
                    os.rmdir(extract_folder)

                # Remove the handler after processing
                app.remove_handler(handle_user_response)

# Ensure you have proper definitions for download_video, download_file, convert_video, and unzip_file functions.

@app.on_message(filters.text & filters.private & filters.user([123456789]))  # Replace with your admin user ID
def handle_zip_file(client, message):
    zip_link = message.text
    zip_file_path = "downloaded_file.zip"
    extract_folder = "extracted_files"

    # Download the zip file
    client.send_message(message.chat.id, "درحال دانلود فایل ZIP...")
    download_file(zip_link, zip_file_path)

    # Create a directory to extract the files
    os.makedirs(extract_folder, exist_ok=True)

    # Unzip the file
    unzip_file(zip_file_path, extract_folder)

    # Send the extracted files back to the user
    for root, dirs, files in os.walk(extract_folder):
        for file in files:
            file_path = os.path.join(root, file)
            client.send_document(chat_id=message.chat.id, document=file_path)

    # Clean up
    os.remove(zip_file_path)
    for file in os.listdir(extract_folder):
        os.remove(os.path.join(extract_folder, file))
    os.rmdir(extract_folder)

app.run()
