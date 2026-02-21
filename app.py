
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os, json, random
import app as app_module  # <-- this imports your app.py
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
word_data = {0: [], 1: []}

# 1️⃣ Load daily words (tword_cat0.json → word_data[0])
daily_path = os.path.join(DATA_DIR, "tword_cat0.json")
if os.path.exists(daily_path):
    with open(daily_path, "r", encoding="utf-8") as f:
        word_data[0] = json.load(f)

# 2️⃣ Load all other categories into word_data[1]
for i in range(1, MAX_CAT):
    path = os.path.join(DATA_DIR, f"tword_cat{i}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            words = json.load(f)
            word_data[1].extend(words)

# 3️⃣ Shuffle non-daily words once at startup
random.shuffle(word_data[1])

#################################################
### Simple in-memory rate limit
#################################################
import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request

# ---- Simple per-IP fixed-window limiter ----
class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max = max_requests
        self.window = window_seconds
        self.hits = defaultdict(deque)  # ip -> deque[timestamps]

    def check(self, key: str):
        now = time.time()
        q = self.hits[key]

        # drop expired timestamps
        cutoff = now - self.window
        while q and q[0] < cutoff:
            q.popleft()

        if len(q) >= self.max:
            raise HTTPException(status_code=429, detail="Too Many Requests")
        q.append(now)

def get_client_ip(request: Request) -> str:
    # Respect reverse proxy if present (Render/Netlify often sets this)
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # first IP is original client
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# Tune these:
limiter_newwords = RateLimiter(max_requests=2, window_seconds=60)  # 30/min/IP
limiter_newword  = RateLimiter(max_requests=10, window_seconds=60)  # 60/min/IP

#################################################
#################################################

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
    print(x_api_key, API_KEY);
    return (x_api_key == API_KEY) or (request.query_params.get("key") == API_KEY)



@app.get("/health")
def health(): return {"ok": True}

from typing import List, Tuple

def word_key(w: dict) -> Tuple[str, str]:
    """
    Create a stable unique key for a word entry.
    """
    ww = w.get("word", "")
    if isinstance(ww, list):
        ww = "|".join(ww)
    return (str(w.get("wtype", "")), str(ww))


def word_len(w: dict) -> int:
    ww = w.get("word", "")
    if isinstance(ww, list):
        return max((len(x) for x in ww), default=0)
    return len(ww)


@app.get("/newwords/{num}")
def newwords(
    num: int,
    request: Request,
    count: int = 20,
    x_api_key: str | None = Header(None),
):

    limiter_newwords.check(get_client_ip(request))

    # (optional) also clamp count to prevent abuse
    count = max(1, min(int(count), 50))

    if not auth_ok(request, x_api_key):
        raise HTTPException(status_code=403, detail="Forbidden")

    isWeb = bool(num & 0x800)
    num = num & ~0x800  # remove web flag

    items: List[dict] = []
    used = set()
    idx = None
    max_mob_char = 10 if num >= 1000 else (7 if num >= 700 else 6)

    # 1️⃣ Add daily word (if in daily mode)
    if num in [0, 100, 500, 700, 1000]:
        if not word_data[0]:
            raise HTTPException(status_code=500, detail="No daily words loaded")

        idx = today_index(len(word_data[0]))
        daily = word_data[0][idx]

        used.add(word_key(daily))
        items.append(to_base64(daily, isWeb))

    # 2️⃣ Fill remaining with unique random words
    if not word_data[1]:
        raise HTTPException(status_code=500, detail="No random words loaded")

    count_total = max(1, min(int(count), 20))

    remaining = count_total - len(items)

    for _ in range(remaining):
        chosen = None

        for __ in range(MAX_RETRIES):
            cand = random.choice(word_data[1])

            if word_len(cand) > max_mob_char:
                continue

            k = word_key(cand)
            if k in used:
                continue

            chosen = cand
            used.add(k)
            break

        # fallback if not found within retries
        if chosen is None:
            for cand in word_data[1]:
                k = word_key(cand)
                if k not in used:
                    chosen = cand
                    used.add(k)
                    break

        if chosen:
            items.append(to_base64(chosen, isWeb))

    return {
        "ver": VER,
        "daily_index": idx,
        "count": len(items),
        "items": items
    }


 # v1 Backward-compatible wrapper
@app.get("/newword/{num}")
def newword(
    num: int,
    request: Request,
    x_api_key: str | None = Header(None),
):
    limiter_newword.check(get_client_ip(request))

    batch = newwords(num=num, request=request, count=1, x_api_key=x_api_key)
    items = batch.get("items", [])
    if not items:
        raise HTTPException(status_code=500, detail="No word generated")
    return items[0]

