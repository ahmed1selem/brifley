"""
Real-time Telegram listener for Briefley.

Runs as an async background task inside FastAPI's event loop (started from
app.py's lifespan).  For every new message that arrives on a tracked channel:

  1. Download attached photo / video / web-preview image → static/media/
  2. Classify the text
  3. Embed the text
  4. Ground-truth verify against existing multi-source clusters in Qdrant
  5. Upsert the result into the 'articles' Qdrant collection

The batch telegram_worker in async_ingest.py handles the last-15-messages
history on every 6-hour cycle; this listener covers everything arriving live
between those cycles (seconds latency).

When the next batch run happens it will upsert the same article IDs, which
updates their cluster_id if clustering improved the assignment — so the two
paths are complementary, not conflicting.
"""
import os
import hashlib
import asyncio
import datetime
from typing import Optional, Tuple

from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaWebPage

import classifier
from vdb_helper import VectorDBHelper
from clustering import embed

CORROBORATED_THRESHOLD = float(os.getenv("CORROBORATED_THRESHOLD", "0.75"))
NOVEL_THRESHOLD = float(os.getenv("NOVEL_THRESHOLD", "0.45"))
MEDIA_DIR = "static/media"


def _article_id(channel: str, msg_id: int) -> str:
    """Same deterministic ID as the batch telegram_worker so upserts overwrite, not duplicate."""
    return hashlib.md5(f"tg_{channel}_{msg_id}".encode("utf-8")).hexdigest()


async def _download_media(message) -> Tuple[Optional[str], Optional[str]]:
    """Download any photo, video, or web-page-preview image from a message.

    Returns (image_url, video_url) as server-relative /static/media/... paths.
    Files land in MEDIA_DIR which FastAPI already serves under /static/.
    """
    os.makedirs(MEDIA_DIR, exist_ok=True)
    image_url: Optional[str] = None
    video_url: Optional[str] = None

    try:
        # Direct photo attachment
        if message.photo:
            path = await message.download_media(file=MEDIA_DIR)
            if path:
                image_url = f"/static/media/{os.path.basename(path)}"

        # Web-page preview (e.g. someone shared a news URL — grab the OG thumbnail)
        elif isinstance(message.media, MessageMediaWebPage):
            wp = message.media.webpage
            if hasattr(wp, "photo") and wp.photo:
                path = await message.download_media(file=MEDIA_DIR)
                if path:
                    image_url = f"/static/media/{os.path.basename(path)}"

        # Video or round video note
        if message.video or message.video_note:
            path = await message.download_media(file=MEDIA_DIR)
            if path:
                video_url = f"/static/media/{os.path.basename(path)}"

    except Exception as exc:
        print(f"[TG Listener] Media download failed: {exc}")

    return image_url, video_url


async def run_listener(
    api_id: Optional[str],
    api_hash: Optional[str],
    get_channels_fn,
):
    """Connect to Telegram and stream incoming messages from tracked channels.

    Usage from FastAPI lifespan:
        task = asyncio.create_task(
            run_listener(TG_API_ID, TG_API_HASH, load_current_channels)
        )

    Cancel the task on shutdown — CancelledError is caught here and the client
    disconnects cleanly.
    """
    if not api_id or not api_hash:
        print("[TG Listener] TG_API_ID / TG_API_HASH not set — real-time listener disabled.")
        return

    channels = get_channels_fn()
    if not channels:
        print("[TG Listener] No channels configured — real-time listener disabled.")
        return

    vdb = VectorDBHelper()
    client = TelegramClient("briefley_session", int(api_id), api_hash)

    try:
        await client.connect()

        if not await client.is_user_authorized():
            print("[TG Listener] Session not authorized. Run: python telegram_ingestor.py")
            await client.disconnect()
            return

        print(f"[TG Listener] Connected. Monitoring {len(channels)} channels in real time.")

        @client.on(events.NewMessage(chats=channels))
        async def on_new_message(event):
            text = (event.message.message or "").strip()
            if not text:
                return

            channel_entity = await event.get_chat()
            channel_name = channel_entity.username or str(channel_entity.id)
            article_id = _article_id(channel_name, event.message.id)
            title = text[:80].replace("\n", " ") + ("..." if len(text) > 80 else "")

            # Media first — client must still be connected
            image_url, video_url = await _download_media(event.message)

            # CPU-bound steps offloaded to thread pool so event loop stays responsive
            category = await asyncio.to_thread(classifier.get_cat, text)
            embedding = await asyncio.to_thread(embed, text)

            # Ground-truth: CORROBORATED only when the matched article is in a real cluster
            similar = vdb.search_similar(embedding, top_k=1)
            label = "ORPHAN"
            cluster_id = "-1"

            if similar:
                top = similar[0]
                score = top["score"]
                cid = top["payload"].get("cluster_id")
                in_real_cluster = cid and str(cid) != "-1"

                if score >= CORROBORATED_THRESHOLD and in_real_cluster:
                    label = "CORROBORATED"
                    cluster_id = str(cid)
                elif score >= NOVEL_THRESHOLD:
                    label = "NOVEL"

            payload = {
                "url": f"https://t.me/{channel_name}/{event.message.id}",
                "source_name": channel_name,
                "title": title,
                "category": category,
                "cluster_id": cluster_id,
                "timestamp": (
                    event.message.date.isoformat()
                    if event.message.date
                    else datetime.datetime.now().isoformat()
                ),
                "summary_text": text,
                "image_url": image_url,
                "video_url": video_url,
                "full_text": text,
                "tg_label": label,
            }

            vdb.upsert_article(article_id, embedding, payload)

            icon = "🟢" if label == "CORROBORATED" else ("🟡" if label == "NOVEL" else "🔴")
            print(f"[TG Listener] @{channel_name} | {icon} {label} | {title}")

        await client.run_until_disconnected()

    except asyncio.CancelledError:
        print("[TG Listener] Shutdown requested — disconnecting.")
        await client.disconnect()

    except Exception as exc:
        print(f"[TG Listener] Fatal: {exc}")
        try:
            await client.disconnect()
        except Exception:
            pass
