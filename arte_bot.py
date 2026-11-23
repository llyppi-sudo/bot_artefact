import asyncio
import argparse
import os
import util_llm
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pathlib import Path
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

#load envs
load_dotenv()

#path root
script_dir = Path(__file__).parent.absolute()

POLITICA = "políticas_da_loja.pdf"
FILE_HIST_CHAT = db_path = script_dir / "hist_chat.db"

SYSTEM_BOT = """
Voce e um bot chat, preparado pra responder ao cliente,auxiliar a equipe no atendimento.
O atendimento é uma loja de instrumentos musicais.
Politica: pdf file possui regras da empresa, info da empresa,endereco,contatos atendimento,horario,pagamentos,devolucao,entregas,garantia.
Data files: lista csv files,produtos,caregorias,pedidos,pagamentos,outros.
Rules: Responder seguir a politica de finida.  
Format: Texto formatado para chat do telegram.
Order: Order lists by price.    
Historico: if exist txt file, historico do chat.
Output: 
Texto curto direto,tirar dúvidas do cliente,seguindo as politicas.
"""
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
BRT = timezone(timedelta(hours=-3))

def find_fileSub(dir: str, file: str):
    """
    Search for a files
    """
    dir_path = Path(dir)
    matches = list(dir_path.rglob(file))
    matches = sorted(matches, key=lambda x: x.stat().st_mtime, reverse=True)
    if not matches:
        return None
    return matches

class ArteBot:

    def ask(self,prompt:str,model:str,system:str,files: list[str] = None) -> str|None:
        try:            
            reuslt = util_llm.llm(
                prompt=prompt,
                system=system,
                files=files,
                model=model,
            )
            
            return reuslt
        except Exception as e:
            print(f"Error {e}")
            return None            

async def init_history_db(db_path: Path) -> aiosqlite.Connection:
    """Create chat history"""
    try:            
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(str(db_path))

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NULL,
                created datetime NOT NULL,
                prompt TEXT,
                response TEXT NOT NULL,
                model TEXT
            )
            """
        )
        # await conn.execute(
        #     """
        #     CREATE INDEX IF NOT EXISTS idx_chat_history_chat_time
        #     ON chat_history (chat_id, created)
        #     """
        # )
        await conn.commit()
        return conn
    except Exception as e:
        print(f"Error {e}")
        return None            

async def save_hist(chat_id: int,response: str,date_chat: datetime,
                    prompt: str,model:str= None,db_path: Path= None) -> None:

    """Save a bot result"""
    try:
        if(not db_path):
            raise Exception(f"Not path db")
        
        if(not db_path.exists()):
            await init_history_db(db_path)

        ts = date_chat or datetime.now(BRT)
        iso_ts = ts.astimezone(BRT).strftime(DATE_FORMAT)

        async with aiosqlite.connect(str(db_path)) as conn:
            await conn.execute(
                """
                INSERT INTO chat_history (chat_id, created, prompt, response, model)
                VALUES (?, ?, ?, ?, ?)
                """,
                (chat_id, iso_ts, prompt, response, model),
            )
            await conn.commit()
        print(f"Save {chat_id},{iso_ts}")
    except Exception as e:
        print(f"Error {e}")
    
async def get_hist(chat_id: int,db_path: Path,start_time: Optional[datetime] = None) -> list[dict] | None:
    """Get saved history"""
    try:
        if not db_path or not db_path.exists():
            return None;
    
        query = """
            SELECT top 5 id, chat_id, created, prompt, response, model
            FROM chat_history
            
        """
        conditions: list[str] = []
        params: list = []
        
        if start_time is not None:
            conditions.append("created >= ?")
            iso_ts = start_time.astimezone(BRT).strftime(DATE_FORMAT)
            params.append(iso_ts)
        if chat_id is not None:
            conditions.append("chat_id = ?")
            params.append(chat_id)
        if(len(params) > 0):
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created desc"

        async with aiosqlite.connect(str(db_path)) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]    
    except Exception as e:
        print(f"Error {e}")
        return None 
    
async def main(args_list=None):
    try:
        parser = argparse.ArgumentParser(description="Bot chat")
        parser.add_argument("--prompt", default=None,type=str)
        parser.add_argument("--model", default=None,type=str)
        parser.add_argument("--chatId", default=None,type=str)
        args = parser.parse_args(args_list) # Pass args_list here

        #None args
        if(args_list):
            for field in args_list:
                if (field and field.startswith("-")) :
                    field = field.replace("-","")
                    if getattr(args, field) == "None" or getattr(args, field) == '':
                        setattr(args, field, None)

        if(not args.prompt):
            raise Exception(f"Prompt vazio")

        #FILE POLITICA
        file_policy = find_fileSub(script_dir,POLITICA)
        if(not file_policy or not Path(file_policy[0]).exists()):
            raise Exception(f"Política do bot vazio")
        file_policy = file_policy[0]

        #AUTH GEMNI
        GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        VERTEX_API_KEY = os.getenv("VERTEX_API_KEY")
        if(not VERTEX_API_KEY and not GOOGLE_API_KEY):
            raise Exception(f"Token gemini vazio")
        
        #data files sent bot
        list_csv = find_fileSub(script_dir/"data","*.csv")
        if(not list_csv or len(list_csv) == 0):
            raise Exception(f"No data csv")
        
        data_files = [str(file_policy)]
        data_files.extend(str(f) for f in list_csv)

        #load hist chat
        today = datetime.now(BRT).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        hist = await get_hist(chat_id=args.chatId,db_path=FILE_HIST_CHAT,start_time=today)
        if(hist):
            data_files.append(str(hist))

        #ask bot
        if(not args.model):
            args.model = util_llm.GEMINI_MODEL[4]
        bot = ArteBot()
        result = bot.ask(prompt=args.prompt,
                         model=args.model,
                         system=SYSTEM_BOT,
                         files=data_files)
        if(not result):
           raise Exception(f"LLM result vazio")

        #save hist chat
        print(result)
        await save_hist(chat_id=args.chatId,
                  response=result,
                  date_chat=None,
                  prompt=args.prompt,
                  model=args.model,
                  db_path=FILE_HIST_CHAT)            
        
        return result
    
    except Exception as e:
        print(f"Error {e}")
        return None

if __name__ == "__main__":
    asyncio.run(main())
