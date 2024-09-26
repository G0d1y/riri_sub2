import os
import requests
import subprocess
import json
import threading
import time
from pysrt import SubRipTime
from pyrogram import Client, filters

def add_watermark(input_video, watermark_image, output_video):
    num_threads = os.cpu_count()
    print(num_threads)
    command = [
        'ffmpeg',
        '-i', input_video,
        '-i', watermark_image,
        '-filter_complex', 'overlay=x=10:y=20',
        '-threads', str(num_threads),
        output_video    
    ]
    subprocess.run(command)

watermark_file = 'Watermark.png'
watermarked_video_path = f'watermarked_video.mkv'
add_watermark("video.mp4", watermark_file, watermarked_video_path)