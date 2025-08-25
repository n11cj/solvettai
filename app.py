
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
ALLOWED_ORIGINS = (
    ["http://localhost:8081", "http://127.0.0.1:8081",  # your current dev port
     "http://localhost:19006", "http://127.0.0.1:19006"]  # Expo default
    if ENV == "dev"
    else ["https://your-site.com"]                        # prod
)

MAX_CAT = 6
MAX_MOB_CHAR = 8
MAX_RETRIES = 50
DATA_DIR = "data"

# --- CORS (browser only) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,       # often needed; safe to enable
    allow_methods=["*"],
    allow_headers=["*"],
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

    if num in [0, 100]:
        return word_data[0][0]

    file_select = num % MAX_CAT
    words = word_data[file_select]

    # mobile range: prefer shorter clusters
    for _ in range(MAX_RETRIES):
        chosen = random.choice(words)
        if 100 <= num < 200 and len(chosen["word"]) > MAX_MOB_CHAR:
            continue
        return chosen

    return words[0]  # safe fallback

