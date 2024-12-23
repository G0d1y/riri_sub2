import os
import subprocess
import json
from pysrt import SubRipTime, SubRipItem
import pysrt
import time
cpu_cores = os.cpu_count()
print(f"Available CPU cores: {cpu_cores}")

def create_ts_file(input_video, output_file):
    processing_start_time = time.time()
    if os.path.exists(input_video):
        try:
            cmd = [
                'ffmpeg', '-i', input_video, '-c', 'copy',
                '-f', 'mpegts', '-threads', str(cpu_cores), output_file
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            processing_time = time.time() - processing_start_time
            print(f"create_ts_file: {processing_time:.2f} s")
            if result.returncode != 0:
                print(f"Failed to create {output_file}: {result.stderr.decode()}")
        except Exception as e:
            print(f"Error running FFmpeg for {output_file}: {e}")
    else:
        print(f"Error: {input_video} not found.")

def change_fps(input_file, output_file, new_fps):
    processing_start_time = time.time()
    command = [
        'ffmpeg',
        '-i', input_file,
        '-filter:v', f'fps=fps={new_fps}',
        '-c:a', 'copy',
        '-threads', str(cpu_cores),
        output_file
    ]
    subprocess.run(command)
    processing_time = time.time() - processing_start_time
    print(f"change_fps: {processing_time:.2f} s")
    

def concat_videos(trailer_ts, downloaded_ts, final_output):
    processing_start_time = time.time()
    if os.path.exists(downloaded_ts) and os.path.exists(trailer_ts):
        try:
            with open('concat_list.txt', 'w') as f:
                f.write(f"file '{trailer_ts}'\n")
                f.write(f"file '{downloaded_ts}'\n")

            cmd = [
                'ffmpeg', '-f', 'concat', '-safe', '0', '-i', 'concat_list.txt',
                '-c', 'copy', '-threads', str(cpu_cores), final_output
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            processing_time = time.time() - processing_start_time
            print(f"concat_videos: {processing_time:.2f} s")

            if result.returncode != 0:
                print(f"Failed to concatenate videos: {result.stderr.decode()}")
        except Exception as e:
            print(f"Error concatenating videos: {e}")
    else:
        print("One or both of the .ts files were not found.")

def process_videos(downloaded_video, trailer_video, final_output):
    trailer_ts = 'trailer.ts'
    downloaded_ts = 'downloaded.ts'
    create_ts_file(trailer_video, trailer_ts)
    create_ts_file(downloaded_video, downloaded_ts)
    concat_videos(trailer_ts, downloaded_ts, final_output)
    try:
        os.remove(trailer_ts)
        os.remove(downloaded_ts)
        os.remove('concat_list.txt')
        print("Cleanup: Deleted temporary files.")
    except Exception as e:
        print(f"Error during cleanup: {e}")

def get_video_fps(video_path):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,bit_rate,r_frame_rate', '-of', 'json', video_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        video_info = json.loads(result.stdout)

        if 'streams' not in video_info or len(video_info['streams']) == 0:
            raise ValueError(f"Video stream info not found in {video_path}. Please check if the file is a valid video.")
        fps_str = video_info['streams'][0].get('r_frame_rate', '0/1')
        fps = eval(fps_str) if fps_str else 0

        return fps

    except Exception as e:
        print(f"Error getting video info: {e}")
        return None, None, None, None
    
def seconds_to_subrip_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return SubRipTime(hours=hours, minutes=minutes, seconds=secs, milliseconds=milliseconds)

def shift_subtitles(subtitle_file, delay_seconds, delay_milliseconds=0):
    print("~~~~~~~~ SHIFTING SOFTSUB ~~~~~~~~")
    subs = pysrt.open(subtitle_file)
    delay = SubRipTime(seconds=delay_seconds, milliseconds=delay_milliseconds)
    for sub in subs:
        sub.start = sub.start + delay
        sub.end = sub.end + delay
    shifted_subtitle_file = subtitle_file.replace('.srt', '_shifted.srt')
    subs.save(shifted_subtitle_file, encoding='utf-8')
    return shifted_subtitle_file

def add_soft_subtitle(video_file, subtitle_file, output_file):
    print("~~~~~~~~ ADDING SOFTSUB ~~~~~~~~")
    processing_start_time = time.time()
    subprocess.run([
        'ffmpeg', '-i', video_file, '-i', subtitle_file, 
        '-c', 'copy', '-c:s', 'srt', '-metadata:s:s:0', 'title=@RiRiMovies', 
        '-disposition:s:0', 'default' , '-threads', str(cpu_cores), output_file
    ])
    processing_time = time.time() - processing_start_time
    print(f"add_soft_subtitle: {processing_time:.2f} s")

def low_qulity(input_path, output_path):
    resolution = "256:144"
    command = [
        "ffmpeg", "-i", input_path,
        "-vf", f"scale={resolution}", "-preset", "veryfast", "-crf", "23", "-c:a", "copy", output_path
    ]
    process = subprocess.Popen(command, stderr=subprocess.PIPE, universal_newlines=True)

    process.wait()

def trim_video(input_file, output_file, duration=90):
    subprocess.run([
        'ffmpeg', '-err_detect', 'ignore_err', '-i', input_file, 
        '-t', str(duration), '-c', 'copy' , '-threads', str(cpu_cores), output_file
    ])
    
def get_aac_profile(video_file):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=codec_name,profile', 
             '-of', 'json', video_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        probe = json.loads(result.stdout)
        
        audio_stream = next((stream for stream in probe.get('streams', []) if stream['codec_name'] == 'aac'), None)
        
        if not audio_stream:
            print("No AAC audio stream found.")
            return None

        profile = audio_stream.get('profile', '').lower()
        codec = get_video_codec(video_file)
        if 'lc' in profile:
            if codec == "x264":
                channel_layout = get_audio_channel_layout(video_file)
                if channel_layout in ["stereo", "mono"]:
                    return "x264_LC"
                else:
                    return "x264_LC_5.1"
            elif codec == "x265":
                channel_layout = get_audio_channel_layout(video_file)
                if channel_layout in ["stereo", "mono"]:
                    return "x265_LC"
                else:
                    return "x265_LC_5.1"
        elif 'he' in profile:
            if codec == "x264":
                channel_layout = get_audio_channel_layout(video_file)
                if channel_layout in ["stereo", "mono"]:
                    return "x264_HE"
                else:
                    return "x264_HE_5.1"   
                
                                 
            elif codec == "x265":
                channel_layout = get_audio_channel_layout(video_file)
                if channel_layout in ["stereo", "mono"]:
                    return "x265_HE"
                else:
                    return "x265_HE_5.1"
                
        else:
            return "x264_LC"

    except Exception as e:
        print("Error:", e)
        return None

def get_video_codec(file_path):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name', '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            raise ValueError("Error running ffprobe: " + result.stderr)

        codec_name = result.stdout.strip()
        
        if codec_name == "h264":
            return "x264"
        elif codec_name == "hevc":
            return "x265"
        else:
            return f"Unknown codec: {codec_name}"
    
    except Exception as e:
        return f"Error: {str(e)}"

def get_audio_channel_layout(video_path):
    command = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=channel_layout",
        "-of", "json",
        video_path
    ]
    
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(result.stdout)
        
        if 'streams' in data and data['streams']:
            channel_layout = data['streams'][0].get('channel_layout', 'Unknown')
            return channel_layout
        else:
            return "No audio stream found"
    
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
