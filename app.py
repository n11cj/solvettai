
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os, json, random

from dotenv import load_dotenv
load_dotenv()  # this will pull in .env values automatically

app = FastAPI()



from fastapi.middleware.cors import CORSMiddleware
import os

ENV = os.getenv("ENV", "dev")

# --- Config ---
API_KEY = os.getenv("API_KEY", "dev-key")
ENV = os.getenv("ENV", "dev")


from fastapi.middleware.cors import CORSMiddleware
import os
MAX_CAT = 6
MAX_RETRIES = 20
DATA_DIR = "data"


ENV = os.getenv("ENV", "dev")

if ENV == "dev":
    # allow ANY localhost/127.0.0.1 port (8081, 19006, etc.)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
        allow_methods=["*"],                    # lets OPTIONS pass
        allow_headers=["x-api-key", "content-type", "accept"],
        allow_credentials=True,
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://your-site.com"],  # set your prod web origin(s)
        allow_methods=["*"],
        allow_headers=["x-api-key", "content-type", "accept"],
        allow_credentials=True,
    )



import datetime, zoneinfo
from fastapi import FastAPI

TZ = zoneinfo.ZoneInfo("Europe/London")
VER = 123

def today_index(max_words):
    today = datetime.datetime.now(TZ).date()
    days = (today - datetime.date(2025, 6, 4)).days
    return days % max_words


# --- Load data once ---
word_data = {}
for i in range(MAX_CAT):
    path = os.path.join(DATA_DIR, f"tword_cat{i}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            word_data[i] = json.load(f)

import base64

def to_base64(data: dict, isWeb: bool) -> dict:
    data["ver"] = VER

    # temp fix, remove after next deploy
    if not isWeb:
        data["Desc"] = data["desc"]
        return data

    encoded = data.copy()

    # Encode each letter in the array individually
    if isinstance(encoded["word"], list):
        encoded["word"] = [
            base64.b64encode(w.encode("utf-8")).decode("utf-8")
            for w in encoded["word"]
        ]
    else:
        encoded["word"] = base64.b64encode(encoded["word"].encode("utf-8")).decode("utf-8")

    encoded["desc"] = base64.b64encode(
        encoded.get("desc", "").encode("utf-8")
    ).decode("utf-8")

    # workaround until all platforms are updates
    encoded["Desc"] = encoded["desc"]

    return encoded

def auth_ok(request: Request, x_api_key: str | None):
    return (x_api_key == API_KEY) or (request.query_params.get("key") == API_KEY)



@app.get("/health")
def health(): return {"ok": True}

@app.get("/newword/{num}")
def newword(num: int, request: Request, x_api_key: str | None = Header(None)):

    if not auth_ok(request, x_api_key):
        raise HTTPException(status_code=403, detail="Forbidden")

    # Detect if web flag is set (bitmask)
    isWeb = bool(num & 0x800)

    # Clear the web flag from num
    num = num & ~0x800

     #print("num ", num)
    if num in [0, 100, 500, 700, 1000]:
        idx = today_index(len(word_data[0]))
         #print("today_index ",(len(word_data[0])) , idx, word_data[0][0])
        return to_base64(word_data[0][idx], isWeb)

    file_select = num % MAX_CAT
    words = word_data[file_select]

    max_mob_char = 10 if num >= 1000 else (7 if num >= 700 else 6)

    # mobile range: prefer shorter clusters
    for _ in range(MAX_RETRIES):
        chosen = random.choice(words)
        if len(chosen["word"]) > max_mob_char:
            continue
        return to_base64(chosen, isWeb)

    print("Not found correct lenth (file, num) :",  file_select, num)
    return to_base64(words[0], isWeb)  # safe fallback

