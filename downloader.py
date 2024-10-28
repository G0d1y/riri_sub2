import requests
import time
import os
import asyncio
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client

DOWNLOAD_DIRECTORY = "./"
ongoing_downloads = {}

async def download_document(client, document, file_name, chat_id):
    file_path = os.path.join(DOWNLOAD_DIRECTORY, file_name) 
    total_size = int(document.file_size) if document.file_size else 0
    downloaded = 0
    start_time = time.time()

    # Send an initial message and retrieve its ID
    progress_message = await client.send_message(chat_id, "دانلود آغاز شد...")
    message_id = progress_message.id

    # Add the "Cancel" button after getting message_id
    await client.edit_message_reply_markup(
        chat_id,
        message_id,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("لغو", callback_data=f"cancel_{message_id}")]
        ])
    )

    # Initialize cancel event
    cancel_event = asyncio.Event()
    ongoing_downloads[message_id] = {
        "cancel_event": cancel_event,
        "file_path": file_path
    }

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

        if current_time - start_time >= 1:
            message_content = (
                f"دانلود: {downloaded / (1024 * 1024):.2f} MB از {total / (1024 * 1024):.2f} MB\n"
                f"سرعت: {speed:.2f} MB/s\n"
                f"زمان باقی‌مانده: {remaining_time:.2f} ثانیه"
            )
            await client.edit_message_text(chat_id, message_id, message_content)

    try:
        await client.download_media(document, file_path, progress=progress)
        await client.edit_message_text(chat_id, message_id, "دانلود کامل شد!")
        del ongoing_downloads[message_id]
        return file_path
    except asyncio.CancelledError:
        await client.edit_message_text(chat_id, message_id, "دانلود لغو شد!")
        os.remove(file_path)
        del ongoing_downloads[message_id]
        return None
    except Exception as e:
        print(f"Error downloading file: {e}")
        await client.edit_message_text(chat_id, message_id, "خطا در دانلود فایل!")
        del ongoing_downloads[message_id]
        return None

async def download_file(client, url, filename, chat_id):
    progress_message = await client.send_message(
        chat_id, 
        "دانلود آغاز شد..."
    )
    message_id = progress_message.id

    await client.edit_message_reply_markup(
        chat_id,
        message_id,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("لغو", callback_data=f"cancel_{message_id}")]
        ])
    )

    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0
    start_time = time.time()

    cancel_event = asyncio.Event()
    ongoing_downloads[message_id] = {
        "cancel_event": cancel_event,
        "file_path": filename
    }

    with open(filename, 'wb') as f:
        last_update_time = time.time()
        
        for data in response.iter_content(chunk_size=1024):
            if cancel_event.is_set():
                raise asyncio.CancelledError("Download cancelled by user")
            
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
                
                await client.edit_message_text(chat_id, message_id, message_content)
                last_update_time = current_time

    del ongoing_downloads[message_id]
    await client.edit_message_text(chat_id, message_id, "دانلود کامل شد!")
    return filename
