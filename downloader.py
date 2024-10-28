import requests
import time
import os
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import pyrogram
DOWNLOAD_DIRECTORY = "./"

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
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("لغو", callback_data=f"cancel:{message_id}")]])
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
    
    # Create a cancellation flag
    cancellation_flag = False

    async def cancel_download():
        nonlocal cancellation_flag
        cancellation_flag = True

    # Listen for the cancellation request (e.g., from a callback query)
    client.add_handler(pyrogram.CallbackQueryHandler(cancel_download, pattern=f"cancel:{message_id}"))

    with open(filename, 'wb') as f:
        last_update_time = time.time()
        previous_message = ""
        
        for data in response.iter_content(chunk_size=1024):
            if cancellation_flag:  # Check if cancellation is requested
                break
                
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
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("لغو", callback_data=f"cancel:{message_id}")]])
                    )
                    previous_message = message_content
                last_update_time = current_time
    
    # Clean up if download is cancelled
    if cancellation_flag:
        # Optionally remove the incomplete file
        import os
        if os.path.exists(filename):
            os.remove(filename)
        await client.edit_message_text(chat_id, message_id, "دانلود لغو شد.")
    else:
        return filename