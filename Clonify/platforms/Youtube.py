import asyncio
import os
import re
from typing import Union

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

from Clonify.utils.database import is_on_off
from Clonify.utils.formatters import time_to_seconds

# Subprocess errors ko handle karne ke liye
async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        err = errorz.decode("utf-8").lower()
        if "unavailable videos are hidden" in err or "warning" in err:
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")

# Cookies file path check
cookies_file = f"{os.getcwd()}/cookies/cookies.txt"
if not os.path.exists(cookies_file):
    cookies_file = None  # Agar file nahi hai toh None rakhein taaki crash na ho

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        
        for message in messages:
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        return text[entity.offset : entity.offset + entity.length]
            if message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        return None

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        res = (await results.next())["result"]
        if not res:
            return None
        result = res[0]
        title = result["title"]
        duration_min = result["duration"]
        thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        vidid = result["id"]
        duration_sec = int(time_to_seconds(duration_min)) if duration_min else 0
        return title, duration_min, duration_sec, thumbnail, vidid

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        # Format ko flexible banaya taaki error na aaye
        cmd = [
            "yt-dlp",
            "-g",
            "-f", "best[height<=?720][width<=?1280]/best",
            link
        ]
        if cookies_file:
            cmd.insert(1, "--cookies")
            cmd.insert(2, cookies_file)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return 1, stdout.decode().split("\n")[0]
        else:
            return 0, stderr.decode()

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        if videoid:
            link = self.base + link
        loop = asyncio.get_running_loop()

        # Common Options for yt-dlp
        common_opts = {
            "quiet": True,
            "no_warnings": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "cookiefile": cookies_file,
            "outtmpl": "downloads/%(id)s.%(ext)s",
        }

        def audio_dl():
            opts = common_opts.copy()
            opts["format"] = "bestaudio/best"
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(link, download=True)
                return ydl.prepare_filename(info)

        def video_dl():
            opts = common_opts.copy()
            # Naya flexible format logic
            opts["format"] = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
            opts["merge_output_format"] = "mp4"
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(link, download=True)
                return ydl.prepare_filename(info)

        def song_video_dl():
            fpath = f"downloads/{title}.mp4"
            opts = common_opts.copy()
            opts.update({
                "format": f"{format_id}+bestaudio/best",
                "outtmpl": f"downloads/{title}.%(ext)s",
                "merge_output_format": "mp4",
                "prefer_ffmpeg": True
            })
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([link])

        def song_audio_dl():
            opts = common_opts.copy()
            opts.update({
                "format": format_id if format_id else "bestaudio/best",
                "outtmpl": f"downloads/{title}.%(ext)s",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            })
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([link])

        if songvideo:
            await loop.run_in_executor(None, song_video_dl)
            return f"downloads/{title}.mp4"
        elif songaudio:
            await loop.run_in_executor(None, song_audio_dl)
            return f"downloads/{title}.mp3"
        elif video:
            if await is_on_off(1):
                downloaded_file = await loop.run_in_executor(None, video_dl)
                return downloaded_file, True
            else:
                status, result = await self.video(link)
                return (result, None) if status else (None, None)
        else:
            downloaded_file = await loop.run_in_executor(None, audio_dl)
            return downloaded_file, True

    # Baaki functions (title, duration, playlist etc.) same rahenge...
    # Unhe bhi safely handle karne ke liye details() wala logic use karein.
