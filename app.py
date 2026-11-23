import re
import os
import requests
import platform
import inspect
import argparse
import sys
import asyncio
import logging
import arte_bot
import util_llm
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from telegram.helpers import escape_markdown as tg_escape_markdown
from pathlib import Path
from dotenv import load_dotenv
import errno

#load envs
load_dotenv()

#log
log = logging.getLogger(__name__)
OS_TYPE = platform.system().lower().strip()

#PATH  
script_dir = Path(__file__).parent.absolute()

BOT_NAME = ""
BOT_ID = ""
BOT_AUTH_FILE = script_dir / "botauth" / "bot.auth"

#TELEGRAM
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID","7826084005")
TELEGRAM_TOKEN_ONLINE = None
TELEGRAM_TOKEN = [
    os.getenv("TELEGRAM_TOKEN_0"),
    os.getenv("TELEGRAM_TOKEN_1"),
]
#AUX
MAX_OUTPUT = 2048
LIMIT_SEND = 10*1024*1024

# Reduce noise from httpx / telegram internals
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)


def telg_send(msg: str, dest:str) -> str:
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN_ONLINE}/sendMessage"
        payload = {
            "chat_id": dest,
            "text": msg
        }
        response = requests.post(url,json=payload,timeout=3000)

        print(response.json())

    except Exception as e:
        print(f"Error: {e}")
        return None    

async def get_description(update, context):
    try:
        chat_id = update.effective_chat.id
        chat = await context.bot.get_chat(chat_id)
        return chat.description
    except Exception as e:
        log.error(f"Error {e}")
        return None

async def bot_alert_sync(token,text,chatId):
    from aiogram import Bot
    
    async with Bot(token=token) as bot:
        await bot.send_message(chat_id=chatId, text=text)
        # await bot.close();

def bot_alert(update,context,e):
    async def run(update,context,e):
        try:
            chat = update.effective_chat
            user = update.effective_user
            userName = f"{user.full_name}_{user.id}".replace(" ","_")
            time = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            await context.bot.send_message(
                chat_id=TELEGRAM_ADMIN_ID,
                text=f"Chat: {chat.effective_name} {chat.id}\n"+
                    f"User: {userName}\n"+
                    f"{str(e)}\n"+
                    f"Date: {time}\n"
                    )
        except Exception as e:
            log.error(f"Error {e}")
        
    asyncio.create_task(run(update,context,e))
    
async def arteGroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    userName = user.full_name+f"_{user.id}".replace(" ","_")
    try:
        method = inspect.stack()[0].function
        log.info(method)

        app_id = [app_name for app_name,func in GROUP_FUNC.items() if method.startswith(app_name)][0]

        log.info(f"{chat.id} - {chat.title} - {userName}")

        if((not update.message.photo == None and len(update.message.photo))
        or not update.message.document == None):
          await update.message.reply_text("Somente texto/audio")
          return False

        #dir chat
        groupDir = script_dir/ app_id / chat.effective_name.strip().replace(" ", "") / userName
        groupDir.mkdir(parents=True, exist_ok=True)

        prompt = update.message.caption or update.message.text or ""

        #first notification bot
        await update.message.reply_text("⏳Bot digitando...")

        if(not prompt):
            prompt = update.message.caption or update.message.text

        #get model default
        modelAI = await get_description(update, context)
        by = f"\n\n🧠by {modelAI}"

        result = await arte_bot.main(["--prompt",prompt,"--model",modelAI,"--chatId",chat.id])
                    
        if(not result):
            await update.message.reply_text("⏳O atendimento será direcionado, aguarde.")
            log.info(F"Falha LLM {chat.title}")
            return
        
        for chunk_start in range(0, len(result), 4096): 
            text = result[chunk_start:chunk_start + 4096]
            text = re.sub(r'<br\s*/?>', '\n', text)
            text = text.replace("*","")
            
            await update.message.reply_text(f"{text}{by if len(text) < 4096 else ''}")                
        
        log.info("Finished")
        #log
        bot_alert(update,context,method)

    except Exception as e:
        log.error(f"Error {e}")
        bot_alert(update,context,e)

def escape_markdown(text: str) -> str:
    # List of all MarkdownV2 reserved characters
    reserved_chars = r'[]()_*~`>#+-=|{}.!'
    # Only escape if the character DOES NOT have a backslash before it
    pattern = f'(?<!\\\\)([{re.escape(reserved_chars)}])'
    
    return re.sub(pattern, r'\\\1', text)

def escape_no_links(text):
 # Match Markdown links: [text](url)
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'

    parts = []
    last_end = 0

    for match in re.finditer(pattern, text):
        # Escape text before the link
        before = text[last_end:match.start()]
        parts.append(tg_escape_markdown(before, version=2))

        # Keep the Markdown link untouched
        link_text = tg_escape_markdown(match.group(1), version=2)
        url = match.group(2)
        parts.append(f'[{link_text}]({url})')

        last_end = match.end()

    parts.append(tg_escape_markdown(text[last_end:], version=2))
    # Escape remaining text after the last link

    return ''.join(parts)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages (text and photos)"""
    method = inspect.stack()[0].function
    log.info(method)

    chat = update.effective_chat
    user = update.effective_user
    userName = user.full_name+f"_{user.id}".replace(" ","_")

    async def run(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        user = update.effective_user
        userName = user.full_name+f"_{user.id}".replace(" ","_")
        try:

            if(update.edited_message):
                update.message = update.edited_message
            user_query = update.message.text or update.message.caption
            if(user_query and user_query.startswith("@")):
                return False                        

            #select func by group
            for app_name, funcGroup in GROUP_FUNC.items():
                if app_name.lower() in chat.effective_name.lower():
                    await funcGroup(update, context)                        
                    return True
                
            return False
        
        except Exception as e:
            log.error(f"Error {e}", exc_info=True)
            bot_alert(update,context,e)
            return False       
    
    asyncio.create_task(run(update,context))
    log.info(f"{method} Chat:{chat.effective_name}/{chat.id} User:{userName} MSG:{update.update_id}")
    return True

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the Telegram framework"""
    log.error("Exception while handling an update:", exc_info=context.error)
    # Check if update is a telegram Update and has a message to reply to
    if isinstance(update, Update) and hasattr(update, "effective_message") and update.effective_message:
        await update.effective_message.reply_text(f"Bot encountered an Error {str(context.error)}")

async def get_bot(token:str):
    """Synchronously get the bot's username at startup"""
    try:
        bot = Bot(token=token)
        bot_info = await bot.get_me()

        global BOT_ID,BOT_NAME,TELEGRAM_TOKEN_ONLINE
        BOT_ID = bot_info.id
        BOT_NAME = bot_info.first_name
        TELEGRAM_TOKEN_ONLINE = token

        return bot_info
    except Exception as e:
        log.error(f"Error {e}")
        return None

class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except OSError as e:
            # Ignore Errno 29 (ESPIPE - Illegal seek) from systemd journal sockets
            if e.errno == errno.ESPIPE or e.errno == 29:
                return
            self.handleError(record)
        except Exception:
            self.handleError(record)

    def flush(self):
        if self.stream and hasattr(self.stream, "flush"):
            try:
                self.stream.flush()
            except OSError as e:
                if e.errno == errno.ESPIPE or e.errno == 29:
                    return
            except Exception:
                return

def initLog(botName: str):
    global log  

    ts = datetime.now().strftime("%Y%m%d")
    lof_file = script_dir / botName.strip() / f"botAI_{ts}.log"
    print(f"Log path {lof_file}")

    if not lof_file.exists():
        lof_file.parent.mkdir(parents=True, exist_ok=True)
        lof_file.touch(exist_ok=True)

    stream_handler = SafeStreamHandler(sys.stdout)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(str(lof_file), encoding="utf-8"),
            stream_handler
        ],
        force=True,
    )
    
    log.info(f"Bot {botName} starting — log: {lof_file}")

GROUP_FUNC = {
                arteGroup.__name__.replace("Group","").lower(): arteGroup,
            }                  
# APPS_AI = ["aichat","house","face","medic","bird","mirror","coin","imovel","car"]            
APPS_GROUPS = [app_name for app_name,func in GROUP_FUNC.items()]
APPS_GROUPS.append("dev")# last dev bot master

async def main(args_list=None):
    parser = argparse.ArgumentParser(description="Telegram AI Bot")
    parser.add_argument("--tokenBot", default=TELEGRAM_TOKEN[1],type=str)
    args = parser.parse_args(args_list)    

    if(args.tokenBot != None and re.fullmatch(r"^\d{1}$", args.tokenBot) is not None):
        idx = int(args.tokenBot)
        args.tokenBot = TELEGRAM_TOKEN[idx]

    """Run the bot"""
    if not args.tokenBot:
        print("Error TELEGRAM_TOKEN not set")
        return    

    # Create application with generous timeouts to avoid TimedOut on startup
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0, write_timeout=30.0)

    #config bot
    app = Application.builder().token(args.tokenBot).request(request).build()
    # app = Application.builder().token(token).request(request).arbitrary_callback_data(True).build()
    
    # Start bot 
    async def initBot(token,app):
        #auth
        bot_info = await get_bot(token)        
        
        if(not bot_info): 
            print("Bot no auth token")
            return
        
        botName = bot_info.first_name
        #Log path
        initLog(botName)        

        #APPS
        log.info("Groups online")
        for app_name in APPS_GROUPS:
            log.info(app_name)

        await bot_alert_sync(token,"Bot online",TELEGRAM_ADMIN_ID)

    asyncio.create_task(initBot(args.tokenBot,app))

    # Add handlers
    app.add_error_handler(error_handler)
    app.add_handler(MessageHandler((filters.TEXT |
                                    filters.PHOTO | 
                                    filters.Document.ALL |
                                    filters.VIDEO | 
                                    filters.VOICE | 
                                    filters.AUDIO) & ~filters.COMMAND, handle_message, block=False))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    await asyncio.Event().wait() 
    # app.run_polling(timeout=30)


if __name__ == "__main__":
    asyncio.run(main())