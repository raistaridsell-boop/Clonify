import logging
from logging.handlers import RotatingFileHandler

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        # RotatingFileHandler use karna behtar hai taki log file bohot badi na ho jaye
        RotatingFileHandler("log.txt", maxBytes=5000000, backupCount=5),
        logging.StreamHandler(),
    ],
)

# In libraries ke purane version ke faltu errors ko hide karne ke liye
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("pytgcalls").setLevel(logging.ERROR)
# Niche wala line 'UpdateGroupCall' jaise errors ko suppress karne me help karega
logging.getLogger("pyrogram.dispatcher").setLevel(logging.CRITICAL) 

def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
