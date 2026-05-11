import asyncio
import importlib
from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

import config
from Clonify import LOGGER, app, userbot
from Clonify.core.call import PRO
from Clonify.misc import sudo
from Clonify.plugins import ALL_MODULES
from Clonify.utils.database import get_banned_users, get_gbanned
from config import BANNED_USERS
from Clonify.plugins.tools.clone import restart_bots

async def init():
    # 1. String Session check
    if not config.STRING1:
        LOGGER("Clonify").error("String Session not filled, please provide a valid session.")
        return # exit() ki jagah return use karna clean hota hai

    # 2. Sudo users aur Banned users load karna
    await sudo()
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except Exception as e:
        LOGGER("Clonify").warning(f"Banned users load nahi ho paye: {e}")

    # 3. App start karna
    await app.start()
    
    # 4. Modules load karna (with error handling)
    for all_module in ALL_MODULES:
        try:
            importlib.import_module("Clonify.plugins" + all_module)
        except Exception as e:
            LOGGER("Clonify.plugins").error(f"Module {all_module} load karne me error: {e}")

    LOGGER("Clonify.plugins").info("𝐀𝐥𝐥 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬 𝐋𝐨𝐚𝐝𝐞𝐝 𝐁𝐚𝐛𝐲🥳...")

    # 5. Userbot aur Call start karna
    await userbot.start()
    await PRO.start()

    # 6. Stream startup check
    try:
        await PRO.stream_call("https://te.legra.ph/file/29f784eb49d230ab62e9e.mp4")
    except NoActiveGroupCall:
        LOGGER("Clonify").error(
            "𝗣𝗹𝗭 𝗦𝗧𝗔𝗥𝗧 𝗬𝗢𝗨𝗥 𝗟𝗢𝗚 𝗚𝗥𝗢𝗨𝗣 𝗩𝗢𝗜𝗖𝗘𝗖𝗛𝗔𝗧/𝗖𝗛𝗔𝗡𝗡𝗘𝗟\n\n𝗠𝗨𝗦𝗜𝗖 𝗕𝗢𝗧 𝗦𝗧𝗢𝗣........"
        )
        return
    except Exception as e:
        LOGGER("Clonify").error(f"Stream start error: {e}")

    await PRO.decorators()
    await restart_bots()
    
    LOGGER("Clonify").info(
        "╔═════ஜ۩۞۩ஜ════╗\n  ☠︎︎𝗠𝗔𝗗𝗘 𝗕𝗬 SPOTIFY BOTS ☠︎︎\n╚═════ஜ۩۞۩ஜ════╝"
    )
    
    # 7. Idle mode (Bot chalta rahega)
    await idle()
    
    # 8. Shutdown process
    await app.stop()
    await userbot.stop()
    LOGGER("Clonify").info("𝗦𝗧𝗢𝗣 𝗠𝗨𝗦𝗜𝗖🎻 𝗕𝗢𝗧..")

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(init())
    except KeyboardInterrupt:
        LOGGER("Clonify").info("Bot manual stop kiya gaya.")
    except Exception as e:
        LOGGER("Clonify").critical(f"Bot crash ho gaya: {e}")
