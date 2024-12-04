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
    last_update_time = 0  

    async def progress(current, total):
        nonlocal downloaded, last_update_time
        downloaded = current
        current_time = time.time()
        elapsed_time = current_time - start_time
        
        if elapsed_time > 0:
            speed = (downloaded / (1024 * 1024)) / elapsed_time
            remaining_time = (total_size - downloaded) / (speed * 1024 * 1024) if speed > 0 else float('inf')
        else:
            speed = 0
            remaining_time = float('inf')

        
        if current_time - last_update_time >= 2:
            last_update_time = current_time
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

    if not filename:
        filename = os.path.basename(url)

    with open(filename, 'wb') as f:
        last_update_time = time.time()
        previous_message = ""
        
        
        low_speed_start_time = None
        is_speed_low = False
        
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
            
            
            if speed < 1:
                if not low_speed_start_time:
                    low_speed_start_time = current_time  
                elif current_time - low_speed_start_time >= 10:
                    if not is_speed_low:
                        
                        await client.edit_message_text(
                            chat_id,
                            message_id,
                            "⏸️ سرعت دانلود پایین است! دانلود ادامه خواهد داشت! 🔄",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("لغو", callback_data=f"cancel:{message_id}")]
                            ])
                        )
                        is_speed_low = True  
                    
                    return await download_file(client, url, filename, chat_id, message_id)

            else:
                low_speed_start_time = None  
            
            
            if current_time - last_update_time >= 1:
                message_content = (
                    f"دانلود: {downloaded / (1024 * 1024):.2f} MB از {total_size / (1024 * 1024):.2f} MB\n"
                    f"سرعت: {speed:.2f} MB/s\n"
                    f"زمان باقی‌مانده: {remaining_time:.2f} ثانیه"
                )
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("لغو", callback_data=f"cancel:{message_id}")]
                ])

                if message_content != previous_message:
                    await client.edit_message_text(
                        chat_id,
                        message_id,
                        message_content,
                        reply_markup=keyboard
                    )
                    previous_message = message_content
                last_update_time = current_time

    print("Download completed.")

    
    if filename.endswith('.zip'):
        extracted_srt_file = None
        with zipfile.ZipFile(filename, 'r') as zip_ref:
            zip_ref.extractall(DOWNLOAD_DIRECTORY)

            extracted_files = zip_ref.namelist()

            for file in extracted_files:
                if file.endswith('.srt'):
                    extracted_srt_file = os.path.join(DOWNLOAD_DIRECTORY, file)
                    print(f"Extracted: {extracted_srt_file}")
                    break

        os.remove(filename)

        if extracted_srt_file:
            new_srt_name = os.path.splitext(filename)[0] + '.srt'
            os.rename(extracted_srt_file, new_srt_name)
            return new_srt_name

    return filename

async def handle_redownload(client, chat_id, message_id, url, filename):
    print(f"Redownload button pressed for message: {message_id}")
    
    await client.edit_message_text(
        chat_id,
        message_id,
        "دانلود دوباره شروع شد... ⏳",
        reply_markup=None
    )
    
    await download_file(client, url, filename, chat_id, message_id)
