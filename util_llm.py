import inspect
import os
import base64
import magic
import platform
from pathlib import Path
from google import genai
from google.genai import types

OS_TYPE = platform.system().lower().strip()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
VERTEX_API_KEY = os.getenv("VERTEX_API_KEY")
GEMINI_MODEL = [
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-3-flash-preview"
        ]

def llm(prompt: str, system: str, files: list[str] = None, model: str = None,json_rst:bool=False) -> str:
    method = inspect.stack()[0].function
    print(method)

    if(not model or model=='None'):
        model = GEMINI_MODEL[0]

    if "gemini-" in model:
        return gemini(prompt, system=system, files=files, model=model,json_rst=json_rst)
    # return ollama(prompt, system=system, files=files, model=model)

def gemini(prompt:str,system:str=None,files:list[str]=None,model:str=GEMINI_MODEL[0],json_rst:bool=False):
    try:
        method = inspect.stack()[0].function
        print(method)

        # model = genai.GenerativeModel(GEMINI_MODEL)
        # response = model.generate_content(prompt)
        if(not model or model=='None'):
            model = GEMINI_MODEL[0]
        # print(prompt)
        print(model)

        prompt_parts = [
            types.Part.from_text(text=prompt),
        ]
        if(files):
            for f in files:
                if(not f or f.strip()==""): continue
                #not file
                if(not os.path.isfile(f)):
                    prompt_parts.append(types.Part.from_text(text=f))
                    continue
                #read file
                print(f"Parts {Path(f).name}")
                with open(f, "rb") as _file:
                    file_bytes = _file.read()
                encoded_string = base64.b64encode(file_bytes).decode('utf-8')
                mime = magic.from_buffer(file_bytes, mime=True)                
                print(f"{mime}")
                if("json" in mime):mime="text/plain"
                prompt_parts.append(types.Part.from_bytes(
                    data= encoded_string,
                    mime_type= mime
                ))

        # 2. Package it into the configuration object
        config = None
        if(system):
            config = types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.1, # Optional parameter
            )
            if json_rst:
                config.response_mime_type="application/json"            

        # client = genai.Client(api_key=GEMINI_API_KEY)
        if(VERTEX_API_KEY):
            client = genai.Client(vertexai=True, api_key=VERTEX_API_KEY)
        elif(GOOGLE_API_KEY):
            client = genai.Client(api_key=GOOGLE_API_KEY)
        response = client.models.generate_content(
            model=model,
            contents=prompt_parts,  
            config=config
        )
        result_text = response.text.strip()

        return result_text
    except Exception as e:        
        print(f"Error {e}")
        return None
