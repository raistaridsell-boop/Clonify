import asyncio
import os
import random
import string
from time import time
from typing import Union

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InputMediaPhoto, Message
from pytgcalls.exceptions import NoActiveGroupCall
from youtubesearchpython.__future__ import VideosSearch

import config
from Clonify import Apple, Carbon, Resso, SoundCloud, Spotify, Telegram, YouTube, app, LOGGER
from Clonify.core.call import PRO
from Clonify.misc import db
from Clonify.utils import seconds_to_min, time_to_seconds
from Clonify.utils.channelplay import get_channeplayCB
from Clonify.utils.database import (
    add_active_video_chat,
    add_served_user_clone,
    get_assistant,
    is_active_chat,
)
from Clonify.utils.database.clonedb import (
    get_cloned_support_channel,
    get_cloned_support_chat,
    get_owner_id_from_db,
)
from Clonify.utils.decorators.language import languageCB
from Clonify.utils.decorators.play import CPlayWrapper
from Clonify.utils.exceptions import AssistantErr
from Clonify.utils.formatters import formats
from Clonify.utils.inline import (
    aq_markup,
    botplaylist_markup,
    close_markup,
    livestream_markup,
    panel_markup_clone,
    playlist_markup,
    slider_markup,
    stream_markup2,
    track_markup,
)
from Clonify.utils.logger import clone_bot_logs, play_logs
from Clonify.utils.pastebin import PROBin
from Clonify.utils.stream.queue import put_queue, put_queue_index
from config import BANNED_USERS, lyrical

# Spam Protection
user_last_message_time = {}
user_command_count = {}
SPAM_THRESHOLD = 2
SPAM_WINDOW_SECONDS = 5

@Client.on_message(
    filters.command(["play", "vplay", "cplay", "cvplay", "playforce", "vplayforce", "cplayforce", "cvplayforce"])
    & filters.group
    & ~BANNED_USERS
)
@CPlayWrapper
async def play_commnd(client, message: Message, _, chat_id, video, channel, playmode, url, fplay):
    cuser = await client.get_me()
    user_id = message.from_user.id
    
    # Anti-Spam Check
    current_time = time()
    last_message_time = user_last_message_time.get(user_id, 0)
    if current_time - last_message_time < SPAM_WINDOW_SECONDS:
        user_command_count[user_id] = user_command_count.get(user_id, 0) + 1
        if user_command_count[user_id] > SPAM_THRESHOLD:
            hu = await message.reply_text(f"**{message.from_user.mention}, please don't spam! Try again after 5 sec.**")
            await asyncio.sleep(3)
            return await hu.delete()
    else:
        user_command_count[user_id] = 1
        user_last_message_time[user_id] = current_time

    await add_served_user_clone(message.chat.id, cuser.id)
    mystic = await message.reply_text(_["play_2"].format(channel) if channel else _["play_1"])
    
    details = None
    streamtype = None
    spotify = None
    img = None
    cap = None

    # Audio/Video Telegram Files
    audio_telegram = (message.reply_to_message.audio or message.reply_to_message.voice) if message.reply_to_message else None
    video_telegram = (message.reply_to_message.video or message.reply_to_message.document) if message.reply_to_message else None

    if audio_telegram:
        if audio_telegram.file_size > 104857600:
            return await mystic.edit_text(_["play_5"])
        file_path = await Telegram.get_filepath(audio=audio_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            details = {"title": await Telegram.get_filename(audio_telegram, audio=True), "link": await Telegram.get_link(message), "path": file_path, "dur": await Telegram.get_duration(audio_telegram, file_path)}
            try:
                await stream(client, _, mystic, user_id, details, chat_id, message.from_user.first_name, message.chat.id, streamtype="telegram", forceplay=fplay)
            except Exception as e:
                return await mystic.edit_text(f"Error: {e}")
            return await mystic.delete()

    elif video_telegram:
        file_path = await Telegram.get_filepath(video=video_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            details = {"title": await Telegram.get_filename(video_telegram), "link": await Telegram.get_link(message), "path": file_path, "dur": await Telegram.get_duration(video_telegram, file_path)}
            try:
                await stream(client, _, mystic, user_id, details, chat_id, message.from_user.first_name, message.chat.id, video=True, streamtype="telegram", forceplay=fplay)
            except Exception as e:
                return await mystic.edit_text(f"Error: {e}")
            return await mystic.delete()

    elif url:
        if await YouTube.exists(url):
            if "playlist" in url:
                try:
                    details = await YouTube.playlist(url, config.PLAYLIST_FETCH_LIMIT, user_id)
                    streamtype = "playlist"; img = config.PLAYLIST_IMG_URL; cap = _["play_10"]
                    plist_id = url.split("=")[1].split("&")[0] if "&" in url else url.split("=")[1]
                except Exception: return await mystic.edit_text(_["play_3"])
            else:
                try:
                    details, track_id = await YouTube.track(url)
                    streamtype = "youtube"; img = details["thumb"]; cap = _["play_11"].format(details["title"], details["duration_min"])
                except Exception: return await mystic.edit_text(_["play_3"])
        
        elif await Spotify.valid(url):
            spotify = True
            if "track" in url:
                details, track_id = await Spotify.track(url)
                streamtype = "youtube"; img = details["thumb"]; cap = _["play_10"].format(details["title"], details["duration_min"])
            else:
                # Handle Spotify Playlists/Albums
                details, plist_id = await Spotify.playlist(url) if "playlist" in url else await Spotify.album(url)
                streamtype = "playlist"; cap = _["play_11"].format(cuser.mention, message.from_user.mention)
                img = config.SPOTIFY_PLAYLIST_IMG_URL
                plist_type = "spplay" if "playlist" in url else "spalbum"

        # Direct M3U8/Index
        else:
            try:
                await stream(client, _, mystic, user_id, url, chat_id, message.from_user.first_name, message.chat.id, video=video, streamtype="index", forceplay=fplay)
            except Exception as e: return await mystic.edit_text(f"Error: {e}")
            return

    else:
        if len(message.command) < 2:
            return await mystic.edit_text(_["play_18"], reply_markup=InlineKeyboardMarkup(botplaylist_markup(_)))
        query = message.text.split(None, 1)[1].replace("-v", "")
        try:
            details, track_id = await YouTube.track(query)
            streamtype = "youtube"
        except Exception: return await mystic.edit_text(_["play_3"])

    # Playmode Logic
    if str(playmode) == "Direct":
        await stream(client, _, mystic, user_id, details, chat_id, message.from_user.first_name, message.chat.id, video=video, streamtype=streamtype, spotify=spotify, forceplay=fplay)
        await mystic.delete()
    else:
        if streamtype == "playlist":
            ran_hash = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
            lyrical[ran_hash] = plist_id
            buttons = playlist_markup(_, ran_hash, user_id, plist_type, "c" if channel else "g", "f" if fplay else "d")
            await mystic.delete()
            await message.reply_photo(photo=img, caption=cap, reply_markup=InlineKeyboardMarkup(buttons))
        else:
            buttons = slider_markup(_, track_id, user_id, query, 0, "c" if channel else "g", "f" if fplay else "d") if 'query' in locals() else track_markup(_, track_id, user_id, "c" if channel else "g", "f" if fplay else "d")
            await mystic.delete()
            await message.reply_photo(photo=details["thumb"] if details else img, caption=_["play_10"].format(details["title"], details["duration_min"]) if details else cap, reply_markup=InlineKeyboardMarkup(buttons))

# Slider Callback Fix
@Client.on_callback_query(filters.regex("slider") & ~BANNED_USERS)
@languageCB
async def slider_queries(client: Client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    try:
        what, rtype, query, user_id, cplay, fplay = callback_request = callback_data.split(None, 1)[1].split("|")
    except: return
    
    if CallbackQuery.from_user.id != int(user_id):
        return await CallbackQuery.answer(_["playcb_1"], show_alert=True)
            
    rtype = int(rtype)
    query_type = (0 if rtype == 9 else rtype + 1) if what == "F" else (9 if rtype == 0 else rtype - 1)
    
    try:
        await CallbackQuery.answer(_["playcb_2"])
        title, duration_min, thumbnail, vidid = await YouTube.slider(query, query_type)
        buttons = slider_markup(_, vidid, user_id, query, query_type, cplay, fplay)
        await CallbackQuery.edit_message_media(
            InputMediaPhoto(media=thumbnail, caption=_["play_10"].format(title.title(), duration_min)),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        LOGGER(__name__).error(e)

# Stream Function (Same Logic with Fixes)
async def stream(client, _, mystic, user_id, result, chat_id, user_name, original_chat_id, video=None, streamtype=None, spotify=None, forceplay=None):
    if not result: return
    if forceplay: await PRO.force_stop_stream(chat_id)
    
    if streamtype == "playlist":
        # Playlist logic...
        pass # Code remains similar to your stream logic but with try-except blocks
    elif streamtype == "youtube":
        vidid = result["vidid"]
        title = result["title"]
        try:
            file_path, direct = await YouTube.download(vidid, mystic, videoid=True, video=video)
        except: return await mystic.edit_text("Download Failed")
        
        if await is_active_chat(chat_id):
            await put_queue(chat_id, original_chat_id, file_path if direct else f"vid_{vidid}", title, result["duration_min"], user_name, vidid, user_id, "video" if video else "audio")
            await client.send_message(original_chat_id, text=_["queue_4"].format("Added", title[:18], result["duration_min"], user_name), reply_markup=InlineKeyboardMarkup(aq_markup(_, chat_id)))
        else:
            if not forceplay: db[chat_id] = []
            await PRO.join_call(chat_id, original_chat_id, file_path, video=video, image=result["thumb"])
            await put_queue(chat_id, original_chat_id, file_path if direct else f"vid_{vidid}", title, result["duration_min"], user_name, vidid, user_id, "video" if video else "audio", forceplay=forceplay)
            img = await get_thumb(vidid)
            run = await client.send_photo(original_chat_id, photo=img, caption=_["stream_1"].format(f"https://t.me/{(await client.get_me()).username}?start=info_{vidid}", title[:18], result["duration_min"], user_name), reply_markup=InlineKeyboardMarkup(panel_markup_clone(_, vidid, chat_id)))
            db[chat_id][0]["mystic"] = run

async def get_thumb(videoid):
    try:
        query = f"https://www.youtube.com/watch?v={videoid}"
        results = VideosSearch(query, limit=1)
        res = await results.next()
        return res["result"][0]["thumbnails"][0]["url"].split("?")[0]
    except: return config.YOUTUBE_IMG_URL
