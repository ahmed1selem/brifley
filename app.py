"""
Briefley — FastAPI Web Server v2.0
Serves the dashboard UI, exposes JSON API endpoints, and runs
background ingestion on a configurable schedule.
"""
import os
import sys
import io
import datetime
import asyncio
import threading
import time
from collections import defaultdict
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from qdrant_client import QdrantClient
import uvicorn
import json
from dotenv import load_dotenv

load_dotenv()

TG_API_ID = os.getenv("TG_API_ID")
TG_API_HASH = os.getenv("TG_API_HASH")

# ==========================================
# RSS FEED URL MAPPING (Name → URL)
# ==========================================
SOURCES_FILE = "sources_config.json"

def load_sources():
    if not os.path.exists(SOURCES_FILE):
        default_sources = {
            "AVAILABLE_RSS_FEEDS": {
                "CNN World":        "http://rss.cnn.com/rss/edition_world.rss",
                "BBC World":        "https://feeds.bbci.co.uk/news/world/rss.xml",
                "Al Jazeera":       "https://www.aljazeera.com/xml/rss/all.xml",
                "Reuters":          "https://feeds.reuters.com/reuters/worldNews",
                "The Guardian":     "https://www.theguardian.com/world/rss",
                "Fox News":         "https://moxie.foxnews.com/google-publisher/world.xml",
                "Sky News Arabia":  "https://www.skynewsarabia.com/web/rss",
                "Mada Masr":        "https://www.madamasr.com/en/feed/",
                "Masrawy":          "https://www.masrawy.com/rss/rssfeeds",
                "Daily News Egypt": "https://dailynewsegypt.com/feed/",
                "Egypt Independent":"https://www.egyptindependent.com/feed/",
                "El Watan News":    "https://www.elwatannews.com/rss",
                "Shorouk News":     "https://www.shorouknews.com/rss",
                "Al Masry Al Youm": "https://www.almasryalyoum.com/rss/rssfeeds",
                "Egyptian Streets":  "https://egyptianstreets.com/feed/",
                "Youm7":            "https://www.youm7.com/rss/SectionRss",
                "Al Bawaba":        "https://www.albawaba.com/rss.xml",
                "Ahram Online":     "https://english.ahram.org.eg/UI/Front/Rss.aspx",
                "Coding Horror":    "https://blog.codinghorror.com/rss/"
            },
            "AVAILABLE_RSS_GROUPED": {
                "World News": ["CNN World", "BBC World", "Al Jazeera", "Reuters", "The Guardian"],
                "Middle East & Egypt": ["Mada Masr", "Masrawy", "Daily News Egypt", "Egypt Independent",
                                        "El Watan News", "Shorouk News", "Al Masry Al Youm", "Egyptian Streets",
                                        "Youm7", "Al Bawaba", "Ahram Online"],
                "Other": ["Fox News", "Sky News Arabia", "Coding Horror"]
            },
            "CURATED_TELEGRAM": {
                "Arabic News": ["aljazeera", "SkyNewsArabia_B", "rtarabictelegram"],
                "Palestine & Middle East": ["hanzpal20", "Middle_East_Spectator", "thecradlemedia",
                                             "Faytuks", "ME_Observer_"],
                "Breaking & OSINT": ["AlJazeeraEnglish", "disclosetv", "BNO_News", "atlasnewstelegram",
                                      "IntelPointAlert", "war_monitor"],
                "Geopolitics & Defense": ["DDGeopolitics", "DefenseArab", "geopolitics_live",
                                           "AUKUS_news", "SouthFrontEng"]
            }
        }
        with open(SOURCES_FILE, "w", encoding="utf-8") as f:
            json.dump(default_sources, f, indent=4)
        return default_sources
    
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_sources(data):
    with open(SOURCES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

_src_data = load_sources()
AVAILABLE_RSS_FEEDS = _src_data["AVAILABLE_RSS_FEEDS"]
AVAILABLE_RSS_GROUPED = _src_data["AVAILABLE_RSS_GROUPED"]
CURATED_TELEGRAM = _src_data["CURATED_TELEGRAM"]

CHANNELS_FILE = "channels.txt"
RSS_FILE = "rss_feeds.txt"

# ==========================================
# FILE HELPERS
# ==========================================
def load_current_rss():
    if not os.path.exists(RSS_FILE):
        return []
    with open(RSS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def save_rss(feeds):
    with open(RSS_FILE, "w", encoding="utf-8") as f:
        f.write("# Briefley Custom RSS Feeds\n# Managed via Web UI\n\n")
        for feed in feeds:
            f.write(f"{feed}\n")

def load_current_channels():
    if not os.path.exists(CHANNELS_FILE):
        return []
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        return [line.strip().replace("@", "") for line in f if line.strip() and not line.startswith("#")]

def save_channels(channels):
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        f.write("# Briefley Telegram Channels\n# Managed via Web UI\n\n")
        for c in channels:
            f.write(f"{c}\n")

# ==========================================
# QDRANT DATA FETCHING
# ==========================================
def fetch_feed():
    try:
        client = QdrantClient(host="localhost", port=6333)
        records, _ = client.scroll(collection_name="articles", limit=1000)
    except Exception as e:
        print(f"[Qdrant] Connection error: {e}")
        return [], []

    clusters_map = defaultdict(list)
    noise = []
    telegram_msgs = []

    for record in records:
        payload = record.payload
        cluster_id = payload.get("cluster_id", "-1")

        dt = datetime.datetime.now()
        if "timestamp" in payload:
            try:
                dt = datetime.datetime.fromisoformat(payload["timestamp"]).replace(tzinfo=None)
            except:
                pass
        payload["_dt"] = dt.isoformat()
        payload["formatted_time"] = dt.strftime("%b %d, %I:%M %p")

        source = payload.get("source_name", payload.get("channel", ""))
        if source.startswith("@") or source in [ch for group in CURATED_TELEGRAM.values() for ch in group]:
            telegram_msgs.append(payload)

        if str(cluster_id) == "-1":
            noise.append(payload)
        else:
            clusters_map[cluster_id].append(payload)

    feed_items = []
    for cid, articles in clusters_map.items():
        articles.sort(key=lambda x: x["_dt"], reverse=True)
        feed_items.append({
            "type": "cluster",
            "cluster_id": cid,
            "count": len(articles),
            "articles": articles,
            "main": articles[0],
        })

    for article in noise:
        feed_items.append({
            "type": "standalone",
            "article": article,
        })

    feed_items.sort(key=lambda x: x.get("main", x.get("article", {})).get("_dt", ""), reverse=True)
    telegram_msgs.sort(key=lambda x: x["_dt"], reverse=True)
    return feed_items, telegram_msgs

# ==========================================
# BACKGROUND INGESTION SCHEDULER
# ==========================================
INGEST_INTERVAL_HOURS = 6
_last_ingest_time = None

def run_ingestion_pipeline():
    """Runs the full async_ingest pipeline in a background thread."""
    global _last_ingest_time
    print(f"\n{'='*60}")
    print(f"[Scheduler] Starting ingestion pipeline at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    try:
        # Import here to avoid circular imports at module load
        import async_ingest
        
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(async_ingest.async_main())
        finally:
            loop.close()
        
        _last_ingest_time = datetime.datetime.now().isoformat()
        print(f"[Scheduler] Ingestion completed at {_last_ingest_time}")
    except Exception as e:
        print(f"[Scheduler] Ingestion FAILED: {e}")
        import traceback
        traceback.print_exc()

def scheduler_loop():
    """Background thread that triggers ingestion every N hours."""
    while True:
        run_ingestion_pipeline()
        print(f"[Scheduler] Next ingestion in {INGEST_INTERVAL_HOURS} hours.")
        time.sleep(INGEST_INTERVAL_HOURS * 3600)

# ==========================================
# FASTAPI APP
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the batch ingestion scheduler and real-time Telegram listener."""
    # Batch scheduler runs every N hours in a background thread
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    print(f"[Scheduler] Background ingestion started (every {INGEST_INTERVAL_HOURS}h)")

    # Real-time Telegram listener runs as an async task in this event loop
    from telegram_listener import run_listener
    tg_task = asyncio.create_task(
        run_listener(TG_API_ID, TG_API_HASH, load_current_channels)
    )

    yield

    tg_task.cancel()
    try:
        await tg_task
    except asyncio.CancelledError:
        pass
    print("[Scheduler] Shutting down.")

app = FastAPI(title="Briefley", version="2.0", lifespan=lifespan)

# Serve static assets
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ==========================================
# ROUTES
# ==========================================
@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

@app.get("/api/feed")
async def api_feed():
    items, tg = fetch_feed()
    return {"feed": items, "telegram": tg}

@app.get("/api/settings")
async def api_settings():
    return {
        "active_rss": load_current_rss(),
        "active_channels": load_current_channels(),
        "available_rss": AVAILABLE_RSS_GROUPED,
        "available_channels": CURATED_TELEGRAM,
    }

@app.get("/api/status")
async def api_status():
    return {
        "last_ingest": _last_ingest_time,
        "interval_hours": INGEST_INTERVAL_HOURS,
    }

class TogglePayload(BaseModel):
    name: str
    action: str

@app.post("/api/rss/toggle")
async def toggle_rss(payload: TogglePayload):
    feeds = load_current_rss()
    if payload.action == "add" and payload.name not in feeds:
        feeds.append(payload.name)
    elif payload.action == "remove" and payload.name in feeds:
        feeds.remove(payload.name)
    save_rss(feeds)
    return {"success": True, "feeds": feeds}

@app.post("/api/channels/toggle")
async def toggle_channel(payload: TogglePayload):
    channels = load_current_channels()
    if payload.action == "add" and payload.name not in channels:
        channels.append(payload.name)
    elif payload.action == "remove" and payload.name in channels:
        channels.remove(payload.name)
    save_channels(channels)
    return {"success": True, "channels": channels}

class AddResourcePayload(BaseModel):
    type: str # 'rss', 'newsletter', 'telegram', 'telegram_list'
    name: str # rss name, or username for tg
    url: str = "" # for rss
    category: str = "Other" # Default category

@app.post("/api/resources/add")
async def add_resource(payload: AddResourcePayload):
    src_data = load_sources()
    
    if payload.type in ["rss", "newsletter"]:
        # Substack/Ghost Newsletters use RSS
        src_data["AVAILABLE_RSS_FEEDS"][payload.name] = payload.url
        if payload.category not in src_data["AVAILABLE_RSS_GROUPED"]:
            src_data["AVAILABLE_RSS_GROUPED"][payload.category] = []
        if payload.name not in src_data["AVAILABLE_RSS_GROUPED"][payload.category]:
            src_data["AVAILABLE_RSS_GROUPED"][payload.category].append(payload.name)
        
        # Auto-subscribe
        active_rss = load_current_rss()
        if payload.name not in active_rss:
            active_rss.append(payload.name)
            save_rss(active_rss)
            
    elif payload.type in ["telegram", "telegram_list"]:
        if payload.category not in src_data["CURATED_TELEGRAM"]:
            src_data["CURATED_TELEGRAM"][payload.category] = []
        
        channels_to_add = []
        if payload.type == "telegram_list":
            channels_to_add = [c.strip().replace("@", "") for c in payload.name.split(",") if c.strip()]
        else:
            channels_to_add = [payload.name.replace("@", "")]
            
        for channel in channels_to_add:
            if channel not in src_data["CURATED_TELEGRAM"][payload.category]:
                src_data["CURATED_TELEGRAM"][payload.category].append(channel)
                
        # Auto-subscribe
        active_ch = load_current_channels()
        for channel in channels_to_add:
            if channel not in active_ch:
                active_ch.append(channel)
        save_channels(active_ch)
        
    save_sources(src_data)
    
    # Update global variables in memory
    global AVAILABLE_RSS_FEEDS, AVAILABLE_RSS_GROUPED, CURATED_TELEGRAM
    AVAILABLE_RSS_FEEDS = src_data["AVAILABLE_RSS_FEEDS"]
    AVAILABLE_RSS_GROUPED = src_data["AVAILABLE_RSS_GROUPED"]
    CURATED_TELEGRAM = src_data["CURATED_TELEGRAM"]
    
    # Optionally trigger ingest in background
    # But for now we just return success
    return {"success": True}


class ChatPayload(BaseModel):
    message: str
    cluster_id: Optional[str] = None

@app.post("/api/chat")
async def chat(payload: ChatPayload):
    try:
        from rag_engine import RAGEngine
        engine = RAGEngine()
        reply = engine.ask(payload.message, current_cluster_id=payload.cluster_id)
        return {"response": reply}
    except Exception as e:
        return {"response": f"RAG Engine Error: {e}. Ensure Ollama is running."}

@app.post("/api/ingest/trigger")
async def trigger_ingest():
    """Manually trigger an ingestion run."""
    thread = threading.Thread(target=run_ingestion_pipeline, daemon=True)
    thread.start()
    return {"status": "Ingestion started in background."}

# ==========================================
# ENTRY POINT
# ==========================================
if __name__ == "__main__":
    print("Starting Briefley v2.0 …")
    uvicorn.run("app:app", host="0.0.0.0", port=8050, reload=False)
