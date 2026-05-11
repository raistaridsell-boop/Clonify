import asyncio
import os
from datetime import datetime, timedelta
from typing import Union

from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.exceptions import (
    AlreadyJoinedError,
    NoActiveGroupCall,
    TelegramServerError,
)
from pytgcalls.types import Update
from pytgcalls.types.input_stream import AudioPiped, AudioVideoPiped
from pytgcalls.types.input_stream.quality import HighQualityAudio, MediumQualityVideo
from pytgcalls.types.stream import StreamAudioEnded

import config
from Clonify import LOGGER, YouTube, app
from Clonify.misc import db
from Clonify.utils.database import (
    add_active_chat,
    add_active_video_chat,
    get_lang,
    get_loop,
    group_assistant,
    is_autoend,
    music_on,
    remove_active_chat,
    remove_active_video_chat,
    set_loop,
)
from Clonify.utils.exceptions import AssistantErr
from Clonify.utils.formatters import check_duration, seconds_to_min, speed_converter
from Clonify.utils.inline.play import stream_markup
from Clonify.utils.stream.autoclear import auto_clean
from strings import get_string
from Clonify.utils.thumbnails import get_thumb

autoend = {}
counter = {}

async def _clear_(chat_id):
    db[chat_id] = []
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)

class Call: # Inherit PyTgCalls hataya kyunki niche alag se define hai
    def __init__(self):
        self.userbot1 = Client(
            name="RAUSHANAss1",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING1),
        )
        self.one = PyTgCalls(
            self.userbot1,
            cache_duration=150,
        )

    async def pause_stream(self, chat_id: int):
        await self.one.pause_stream(chat_id)

    async def resume_stream(self, chat_id: int):
        await self.one.resume_stream(chat_id)

    async def stop_stream(self, chat_id: int):
        try:
            await _clear_(chat_id)
            await self.one.leave_group_call(chat_id)
        except Exception:
            pass

    async def stop_stream_force(self, chat_id: int):
        try:
            if config.STRING1:
                await self.one.leave_group_call(chat_id)
        except Exception:
            pass
        try:
            await _clear_(chat_id)
        except Exception:
            pass

    async def speedup_stream(self, chat_id: int, file_path, speed, playing):
        if str(speed) != "1.0":
            base = os.path.basename(file_path)
            chatdir = os.path.join(os.getcwd(), "playback", str(speed))
            if not os.path.isdir(chatdir):
                os.makedirs(chatdir)
            out = os.path.join(chatdir, base)
            if not os.path.isfile(out):
                vs = {"0.5": 2.0, "0.75": 1.35, "1.5": 0.68, "2.0": 0.5}.get(str(speed), 1.0)
                cmd = (
                    f"ffmpeg -i {file_path} -filter:v setpts={vs}*PTS "
                    f"-filter:a atempo={speed} {out} -y"
                )
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
        else:
            out = file_path

        dur = await asyncio.get_event_loop().run_in_executor(None, check_duration, out)
        duration = seconds_to_min(int(dur))
        played, con_seconds = speed_converter(playing[0]["played"], speed)
        
        stream = (
            AudioVideoPiped(
                out,
                audio_parameters=HighQualityAudio(),
                video_parameters=MediumQualityVideo(),
                additional_ffmpeg_parameters=f"-ss {played} -to {duration}",
            )
            if playing[0]["streamtype"] == "video"
            else AudioPiped(
                out,
                audio_parameters=HighQualityAudio(),
                additional_ffmpeg_parameters=f"-ss {played} -to {duration}",
            )
        )
        
        if str(db[chat_id][0]["file"]) == str(file_path):
            await self.one.change_stream(chat_id, stream)
            db[chat_id][0].update({
                "played": con_seconds,
                "dur": duration,
                "seconds": int(dur),
                "speed_path": out,
                "speed": speed
            })
        else:
            raise AssistantErr("Umm")

    async def skip_stream(self, chat_id: int, link: str, video: bool = False):
        stream = AudioVideoPiped(link, HighQualityAudio(), MediumQualityVideo()) if video else AudioPiped(link, HighQualityAudio())
        await self.one.change_stream(chat_id, stream)

    async def join_call(self, chat_id: int, original_chat_id: int, link, video: bool = False):
        _ = get_string(await get_lang(chat_id))
        stream = AudioVideoPiped(link, HighQualityAudio(), MediumQualityVideo()) if video else AudioPiped(link, HighQualityAudio())
        
        try:
            await self.one.join_group_call(chat_id, stream, stream_type=StreamType().pulse_stream)
        except NoActiveGroupCall:
            raise AssistantErr(_["call_8"])
        except AlreadyJoinedError:
            pass # Ignore agar pehle se join hai
        except TelegramServerError:
            raise AssistantErr(_["call_10"])

        await add_active_chat(chat_id)
        await music_on(chat_id)
        if video:
            await add_active_video_chat(chat_id)

    async def ping(self):
        pings = []
        if config.STRING1:
            try:
                pings.append(self.one.ping)
            except:
                pings.append(0)
        return str(round(sum(pings) / len(pings), 3)) if pings else "0"

    async def start(self):
        LOGGER(__name__).info("Starting Assistant Clients...\n")
        if config.STRING1:
            await self.one.start()

    async def decorators(self):
        @self.one.on_kicked()
        @self.one.on_closed_voice_chat()
        @self.one.on_left()
        async def stream_services_handler(_, chat_id: int):
            await self.stop_stream(chat_id)

        @self.one.on_stream_end()
        async def stream_end_handler(client, update: Update):
            if isinstance(update, StreamAudioEnded):
                chat_id = update.chat_id
                # Niche wala function 'change_stream' aapke core/streamer file me hona chahiye
                # Agar error de to check karein ki wo kahan defined hai
                await self.skip_stream(chat_id, "link_here") 

PRO = Call()
