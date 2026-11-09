import os
import sys
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import Message
from datetime import datetime

# Import from our existing project modules
from vdb_helper import VectorDBHelper
from clustering import embed

# Load environment variables
load_dotenv()

API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")
PHONE = os.getenv("TG_PHONE")  # Optional, helps telethon auto-fill

if not API_ID or not API_HASH:
    print("="*60)
    print("ERROR: Missing Telegram API Credentials!")
    print("To run the Telegram Ingestor, you must:")
    print("1. Go to https://my.telegram.org and log in.")
    print("2. Click 'API development tools'.")
    print("3. Create an application to get your API_ID and API_HASH.")
    print("4. Add TG_API_ID and TG_API_HASH to your .env file.")
    print("="*60)
    sys.exit(1)

# Configurable thresholds for Ground-Truth filter
CORROBORATED_THRESHOLD = 0.75
NOVEL_THRESHOLD = 0.45

def load_channels(filename="channels.txt"):
    """Load channels dynamically from a text file."""
    channels = []
    if not os.path.exists(filename):
        print(f"Warning: {filename} not found. Monitoring default channels.")
        return ["aljazeera", "SkyNewsArabia_B", "rtarabictelegram"]
        
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Ignore empty lines and comments
            if line and not line.startswith("#"):
                # Strip @ if user accidentally included it
                if line.startswith("@"):
                    line = line[1:]
                channels.append(line)
    return channels

async def main():
    print("="*60)
    print("Briefley: Real-Time Telegram Ingestor & Ground-Truth Filter")
    print("="*60)
    
    # Initialize VDB and Embedder
    print("Loading Vector DB and Embedder model...")
    vdb = VectorDBHelper()
    print("Models loaded successfully.")
    
    # Load dynamic channels
    channels_to_monitor = load_channels()
    print(f"Monitoring {len(channels_to_monitor)} channels: {', '.join(channels_to_monitor)}")
    
    # Initialize Telethon Client
    client = TelegramClient('briefley_session', API_ID, API_HASH)
    
    print("\nConnecting to Telegram...")
    if PHONE:
        await client.start(phone=PHONE)
    else:
        # Fallback to interactive terminal prompt if no phone in .env
        await client.start()
    print("Connected to Telegram successfully!")
    
    # Register the real-time event listener
    @client.on(events.NewMessage(chats=channels_to_monitor))
    async def handler(event):
        text = event.message.message
        if not text:
            return
            
        channel_entity = await event.get_chat()
        channel_name = channel_entity.username or str(channel_entity.id)
        msg_id = f"{channel_name}_{event.message.id}"
        
        # 1. Embed the Telegram message (stopwords removed for consistency)
        embedding = embed(text)
        
        # 2. Ground-Truth Filter: Compare against verified mainstream news
        similar_articles = vdb.search_similar(embedding, top_k=1)
        
        label = "ORPHAN"
        match_cluster_id = None
        similarity_score = 0.0
        
        if similar_articles:
            top_match = similar_articles[0]
            similarity_score = top_match["score"]
            match_cluster_id = top_match["payload"].get("cluster_id")

            # A match only counts as CORROBORATED when the matched article belongs to
            # a real multi-source cluster (cluster_id != "-1").  Matching a standalone
            # noise article proves nothing — downgrade those to NOVEL at most.
            in_real_cluster = match_cluster_id and str(match_cluster_id) != "-1"

            if similarity_score >= CORROBORATED_THRESHOLD and in_real_cluster:
                label = "CORROBORATED"
            elif similarity_score >= NOVEL_THRESHOLD:
                label = "NOVEL"
        
        # 3. Store in Qdrant
        payload = {
            "channel": channel_name,
            "text": text,
            "full_text": text,
            "label": label,
            "match_cluster_id": match_cluster_id,
            "similarity_score": similarity_score,
            "timestamp": event.message.date.isoformat() if event.message.date else datetime.now().isoformat()
        }
        
        success = vdb.upsert_telegram_message(msg_id, embedding, payload)
        if success:
            color = "🟢" if label == "CORROBORATED" else ("🟡" if label == "NOVEL" else "🔴")
            clean_text = text.replace('\n', ' ')
            print(f"[{datetime.now().strftime('%H:%M:%S')}] @{channel_name} | {color} [{label}] Score: {similarity_score:.2f} | {clean_text[:50]}...")

    print("\nListening for live breaking news... (Press Ctrl+C to stop)")
    await client.run_until_disconnected()

if __name__ == '__main__':
    # Telethon requires an asyncio event loop
    asyncio.run(main())
