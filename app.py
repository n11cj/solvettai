
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

# --- Load data once ---
word_data = {}
for i in range(MAX_CAT):
    path = os.path.join(DATA_DIR, f"tword_cat{i}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            word_data[i] = json.load(f)

def auth_ok(request: Request, x_api_key: str | None):
    return (x_api_key == API_KEY) or (request.query_params.get("key") == API_KEY)

@app.get("/health")
def health(): return {"ok": True}

@app.get("/newword/{num}")
def newword(num: int, request: Request, x_api_key: str | None = Header(None)):
    if not auth_ok(request, x_api_key):
        raise HTTPException(status_code=403, detail="Forbidden")

 # print("num ", num)
    if num in [0, 100, 500, 700, 1000]:
        return word_data[0][0]

    file_select = num % MAX_CAT
    words = word_data[file_select]

    max_mob_char = 10 if num >= 1000 else (7 if num >= 700 else 6)

    # mobile range: prefer shorter clusters
    for _ in range(MAX_RETRIES):
        chosen = random.choice(words)
        if len(chosen["word"]) > max_mob_char:
            continue
        return chosen

    print("Not found correct lenth (file, num) :",  file_select, num)
    return words[0]  # safe fallback

