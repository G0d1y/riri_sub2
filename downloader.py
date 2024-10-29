import requests
import time
import os
import asyncio
import zipfile

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DOWNLOAD_DIRECTORY = "./"
cancel_event = asyncio.Event()

async def download_document(client, document, file_name, chat_id, message_id):
    file_path = os.path.join(DOWNLOAD_DIRECTORY, file_name) 
    
    total_size = int(document.file_size) if document.file_size else 0
    downloaded = 0
    start_time = time.time()

    async def progress(current, total):
        nonlocal downloaded
        downloaded = current
        current_time = time.time()
        elapsed_time = current_time - start_time
        
        if elapsed_time > 0:
            speed = (downloaded / (1024 * 1024)) / elapsed_time
            remaining_time = (total_size - downloaded) / (speed * 1024 * 1024) if speed > 0 else float('inf')
        else:
            speed = 0
            remaining_time = float('inf')

        if int(current / (total / 100)) % 3 == 0:
            message_content = (
                f"دانلود: {downloaded / (1024 * 1024):.2f} MB از {total / (1024 * 1024):.2f} MB\n"
                f"سرعت: {speed:.2f} MB/s\n"
                f"زمان باقی‌مانده: {remaining_time:.2f} ثانیه"
            )
            await client.edit_message_text(
                chat_id,
                message_id,
                message_content,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("لغو", callback_data=f"cancel:{message_id}")]]),
            )    
    try:
        await client.download_media(document, file_path, progress=progress)
        return file_path
    except Exception as e:
        print(f"Error downloading file: {e}")
        return None

async def download_file(client, url, filename, chat_id, message_id):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0
    start_time = time.time()
    
    # Get the filename from the URL if not provided
    if not filename:
        filename = os.path.basename(url)  # Use the last part of the URL as filename
    
    with open(filename, 'wb') as f:
        last_update_time = time.time()
        previous_message = ""
        
        for data in response.iter_content(chunk_size=1024):
            if cancel_event.is_set():
                print("Download cancelled.")
                return None
            
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
                    await client.edit_message_text(
                        chat_id,
                        message_id,
                        message_content,
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("لغو", callback_data=f"cancel:{message_id}")]]),
                    )
                    previous_message = message_content
                last_update_time = current_time
    
    print("Download completed.")

    # Check if the downloaded file is a zip file and extract it
    if filename.endswith('.zip'):
        extracted_srt_file = None
        with zipfile.ZipFile(filename, 'r') as zip_ref:
            zip_ref.extractall(DOWNLOAD_DIRECTORY)
            # Get the list of extracted files
            extracted_files = zip_ref.namelist()
            # Find the first SRT file
            for file in extracted_files:
                if file.endswith('.srt'):
                    extracted_srt_file = os.path.join(DOWNLOAD_DIRECTORY, file)
                    break
        
        # Clean up the ZIP file after extraction
        os.remove(filename)  # Remove the ZIP file
        if extracted_srt_file:
            return extracted_srt_file  # Return the SRT file path

    return filename  # Return the original filename if no SRT file is found
