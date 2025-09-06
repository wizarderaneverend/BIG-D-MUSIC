# Copyright (c) 2025 Nand Yaduwanshi <NoxxOP>
# Location: Supaul, Bihar
# Optimized for ultra-fast performance (1-3 seconds)

import asyncio
import os
import re
import json
import glob
import random
import logging
from typing import Union
from concurrent.futures import ThreadPoolExecutor
import threading
from functools import lru_cache

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

from ShrutiMusic.utils.database import is_on_off
from ShrutiMusic.utils.formatters import time_to_seconds

# Global thread pool for better performance
executor = ThreadPoolExecutor(max_workers=4)

# Cache for cookie file to avoid repeated file system calls
_cookie_cache = None
_cookie_cache_lock = threading.Lock()

@lru_cache(maxsize=32)
def get_cached_cookie_file():
    """Cache cookie file selection for better performance"""
    global _cookie_cache
    if _cookie_cache is None:
        with _cookie_cache_lock:
            if _cookie_cache is None:
                folder_path = f"{os.getcwd()}/cookies"
                txt_files = glob.glob(os.path.join(folder_path, '*.txt'))
                if not txt_files:
                    raise FileNotFoundError("No .txt files found in cookies folder.")
                _cookie_cache = f"cookies/{random.choice(txt_files).split('/')[-1]}"
                
                # Log without file I/O blocking
                filename = f"{os.getcwd()}/cookies/logs.csv"
                try:
                    with open(filename, 'a') as file:
                        file.write(f'Chosen File: {_cookie_cache}\n')
                except:
                    pass  # Don't fail if logging fails
    return _cookie_cache

async def quick_file_size_check(link):
    """Ultra-fast file size check with timeout"""
    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                "yt-dlp", "--cookies", get_cached_cookie_file(),
                "--get-filesize", "--no-warnings", link,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            ),
            timeout=3.0  # 3 second timeout
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0 and stdout:
            size = int(stdout.decode().strip())
            return size / (1024 * 1024)  # Return size in MB
    except (asyncio.TimeoutError, ValueError):
        pass
    return 50  # Default safe size if check fails

class FastYouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = re.compile(r"(?:youtube\.com|youtu\.be)")
        self.listbase = "https://youtube.com/playlist?list="
        
        # Pre-compile common yt-dlp options for speed
        self.base_opts = {
            "quiet": True,
            "no_warnings": True,
            "cookiefile": get_cached_cookie_file(),
            "extract_flat": False,
            "skip_download": True
        }

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(self.regex.search(link))

    async def url(self, message_1: Message) -> Union[str, None]:
        """Fast URL extraction from message"""
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        
        for message in messages:
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        return text[entity.offset:entity.offset + entity.length]
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        return None

    async def quick_details(self, link: str, videoid: Union[bool, str] = None):
        """Ultra-fast details extraction - optimized for speed"""
        if videoid:
            link = self.base + link
        
        link = link.split("&")[0]  # Clean link fast
        
        try:
            # Use asyncio.wait_for with short timeout for speed
            results = await asyncio.wait_for(
                VideosSearch(link, limit=1).next(),
                timeout=2.0
            )
            
            result = results["result"][0]
            title = result["title"]
            duration_min = result["duration"] 
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            
            duration_sec = 0 if str(duration_min) == "None" else int(time_to_seconds(duration_min))
            
            return title, duration_min, duration_sec, thumbnail, vidid
        except (asyncio.TimeoutError, IndexError, KeyError):
            # Fallback for failed searches
            return "Unknown Title", "0:00", 0, "", link.split("=")[-1]

    async def get_stream_url(self, link: str, videoid: Union[bool, str] = None, quality="audio"):
        """Ultra-fast stream URL extraction"""
        if videoid:
            link = self.base + link
        
        link = link.split("&")[0]
        
        try:
            if quality == "audio":
                format_selector = "bestaudio/best"
            else:
                format_selector = "18/best[height<=720]"
            
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    "yt-dlp", "--cookies", get_cached_cookie_file(),
                    "-g", "-f", format_selector, "--no-warnings", link,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                ),
                timeout=4.0
            )
            
            stdout, stderr = await proc.communicate()
            
            if stdout:
                return stdout.decode().split("\n")[0]
            else:
                return None
                
        except asyncio.TimeoutError:
            return None

    async def fast_download(self, link: str, video=False, audio=True):
        """Super fast download with minimal options"""
        if not link:
            return None
            
        def quick_download():
            if audio:
                opts = {
                    "format": "bestaudio/best",
                    "outtmpl": "downloads/%(id)s.%(ext)s",
                    "quiet": True,
                    "no_warnings": True,
                    "cookiefile": get_cached_cookie_file(),
                }
            else:
                opts = {
                    "format": "18/best[height<=720]",
                    "outtmpl": "downloads/%(id)s.%(ext)s", 
                    "quiet": True,
                    "no_warnings": True,
                    "cookiefile": get_cached_cookie_file(),
                }
            
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(link, download=False)
                    file_path = os.path.join("downloads", f"{info['id']}.{info['ext']}")
                    
                    if os.path.exists(file_path):
                        return file_path
                    
                    ydl.download([link])
                    return file_path
            except Exception as e:
                logging.error(f"Download failed: {e}")
                return None
        
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, quick_download)

    async def playlist_quick(self, link, limit=10):
        """Fast playlist extraction"""
        if "&" in link:
            link = link.split("&")[0]
        
        try:
            cmd = f"yt-dlp -i --get-id --flat-playlist --cookies {get_cached_cookie_file()} --playlist-end {limit} --no-warnings {link}"
            
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                ),
                timeout=5.0
            )
            
            stdout, stderr = await proc.communicate()
            
            if stdout:
                result = [vid.strip() for vid in stdout.decode().split("\n") if vid.strip()]
                return result[:limit]
            
        except asyncio.TimeoutError:
            logging.warning("Playlist extraction timed out")
        
        return []

    async def get_direct_url(self, link: str, videoid: Union[bool, str] = None):
        """Get direct playable URL super fast"""
        if videoid:
            link = self.base + link
            
        # Try direct stream URL first (fastest)
        stream_url = await self.get_stream_url(link, quality="audio")
        if stream_url:
            return stream_url, False  # URL, is_downloaded
        
        # Check if we need to download (size check)
        size_mb = await quick_file_size_check(link)
        
        if size_mb > 100:  # If file too large, return None
            return None, False
            
        # Download if needed
        downloaded_file = await self.fast_download(link, audio=True)
        return downloaded_file, True

    # Maintain compatibility with existing code
    async def details(self, link: str, videoid: Union[bool, str] = None):
        return await self.quick_details(link, videoid)
    
    async def title(self, link: str, videoid: Union[bool, str] = None):
        title, _, _, _, _ = await self.quick_details(link, videoid)
        return title
    
    async def duration(self, link: str, videoid: Union[bool, str] = None):
        _, duration, _, _, _ = await self.quick_details(link, videoid)
        return duration
        
    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        _, _, _, thumb, _ = await self.quick_details(link, videoid)
        return thumb

    async def track(self, link: str, videoid: Union[bool, str] = None):
        title, duration_min, _, thumbnail, vidid = await self.quick_details(link, videoid)
        
        if videoid:
            yturl = self.base + link
        else:
            yturl = link
            
        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }
        return track_details, vidid

    # Fast video method for VC
    async def video(self, link: str, videoid: Union[bool, str] = None):
        """Ultra-fast video URL for VC joining"""
        if videoid:
            link = self.base + link
            
        # Get direct stream URL (fastest method)
        stream_url = await self.get_stream_url(link, quality="video")
        
        if stream_url:
            return 1, stream_url
        else:
            return 0, "Failed to get video stream"

# Create optimized instance
YouTubeAPI = FastYouTubeAPI

# ©️ Copyright Reserved - @NoxxOP Nand Yaduwanshi
# Optimized for ultra-fast performance
