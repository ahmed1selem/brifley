import asyncio
import feedparser
import sys
import os
import time
import datetime
import hashlib
import urllib.parse
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

import scraping
import classifier
import summarizer
from clustering import clusters, get_embedder, remove_stopwords
from vdb_helper import VectorDBHelper
from app import AVAILABLE_RSS_FEEDS, load_current_rss, load_current_channels
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()
API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")

MAX_ARTICLES_PER_FEED = 15


def deduplicate_articles(articles, threshold=0.90):
    """
    Remove near-duplicate articles within the same cluster.

    For each cluster (excluding noise cluster '-1'), compute pairwise cosine
    similarity on article summaries.  When two articles exceed *threshold*,
    keep the one with the longer `text` field and discard the other.

    Returns a new list with duplicates removed.
    """
    embedder = get_embedder()

    # Group articles by cluster_id (skip noise)
    cluster_map = {}  # cluster_id -> list of articles
    for article in articles:
        cid = article.get("cluster_id", "-1")
        if cid == "-1":
            continue
        cluster_map.setdefault(cid, []).append(article)

    # Collect IDs of articles to remove
    ids_to_remove = set()

    for cid, group in cluster_map.items():
        if len(group) < 2:
            # Nothing to compare inside a single-article cluster
            continue

        # Encode all summaries in one batch for efficiency
        summaries = [a.get("summary", "") or "" for a in group]
        embeddings = embedder.encode(summaries)
        sim_matrix = cosine_similarity(embeddings)

        # Walk the upper triangle of the similarity matrix
        for i in range(len(group)):
            if group[i]["id"] in ids_to_remove:
                continue
            for j in range(i + 1, len(group)):
                if group[j]["id"] in ids_to_remove:
                    continue
                if sim_matrix[i][j] >= threshold:
                    # Keep the article with more text; discard the other
                    len_i = len(group[i].get("text", "") or "")
                    len_j = len(group[j].get("text", "") or "")
                    loser = group[j] if len_i >= len_j else group[i]
                    ids_to_remove.add(loser["id"])

    # Build the deduplicated list (preserves original order)
    deduped = [a for a in articles if a["id"] not in ids_to_remove]
    return deduped

# Global State Manager for Articles
# Key: article ID
# Value: dict of article data and processing status
article_state = {}
state_lock = asyncio.Lock()

def generate_id(url: str) -> str:
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def get_feed_urls(rss_url, max_items):
    """Synchronous feed fetching to run in thread"""
    print(f"[RSS] Fetching feed: {rss_url}")
    feed = feedparser.parse(rss_url)
    urls = []
    
    if getattr(feed, 'bozo', 0) and type(getattr(feed, 'bozo_exception', None)) != type(None):
        print(f"[RSS Warning] Issue parsing feed {rss_url}: {feed.bozo_exception}")
        
    if feed.entries:
        for entry in feed.entries[:max_items]:
            urls.append(entry.link)
    return urls

async def rss_worker(feed_queue, scrape_queue):
    while True:
        feed_name, rss_url = await feed_queue.get()
        try:
            urls = await asyncio.to_thread(get_feed_urls, rss_url, MAX_ARTICLES_PER_FEED)
            print(f"[RSS] Found {len(urls)} articles for {feed_name}")
            for url in urls:
                article_id = generate_id(url)
                
                async with state_lock:
                    if article_id not in article_state:
                        article_state[article_id] = {
                            "id": article_id,
                            "url": url,
                            "source_name": feed_name,
                            "title": None,
                            "image_url": None,
                            "text": None,
                            "category": None,
                            "summary": None,
                            "timestamp": datetime.datetime.now().isoformat(),
                            "status": "pending_scrape"
                        }
                await scrape_queue.put(article_id)
        except Exception as e:
            print(f"[RSS Error] {feed_name}: {e}")
        finally:
            feed_queue.task_done()

async def scrape_worker(scrape_queue, classify_queue, summarize_queue):
    while True:
        article_id = await scrape_queue.get()
        
        async with state_lock:
            url = article_state[article_id]["url"]
            
        print(f"[Scrape] Starting: {url}")
        try:
            # Run the synchronous scraper in a thread
            cleaned_text, title, img_src = await asyncio.to_thread(scraping.init, url)
            
            if not cleaned_text or cleaned_text.strip() == "":
                cleaned_text = title # Fallback
                
            async with state_lock:
                article_state[article_id]["text"] = cleaned_text
                article_state[article_id]["title"] = title
                article_state[article_id]["image_url"] = img_src
                article_state[article_id]["status"] = "scraped"
                
            if cleaned_text and cleaned_text.strip():
                await classify_queue.put(article_id)
                await summarize_queue.put(article_id)
            else:
                print(f"[Scrape] Skipping empty content for {url}")
        except Exception as e:
            print(f"[Scrape Error] {url}: {e}")
            async with state_lock:
                article_state[article_id]["status"] = "failed"
        finally:
            scrape_queue.task_done()

async def classify_worker(classify_queue):
    while True:
        article_id = await classify_queue.get()
        async with state_lock:
            text = article_state[article_id]["text"]
            url = article_state[article_id]["url"]
            
        try:
            category = await asyncio.to_thread(classifier.get_cat, text)
            async with state_lock:
                article_state[article_id]["category"] = category
            print(f"[Classify] Done: {category} -> {url}")
        except Exception as e:
            print(f"[Classify Error] {url}: {e}")
            async with state_lock:
                article_state[article_id]["category"] = "General News"
        finally:
            classify_queue.task_done()

async def summarize_worker(summarize_queue):
    while True:
        article_id = await summarize_queue.get()
        async with state_lock:
            text = article_state[article_id]["text"]
            title = article_state[article_id]["title"]
            url = article_state[article_id]["url"]
            
        print(f"[Summarize] Starting: {url}")
        try:
            # summarizer uses PyTorch/Pegasus
            if not text or text == title:
                summary = title
            else:
                summary = await asyncio.to_thread(summarizer.summarize, text)
                
            async with state_lock:
                article_state[article_id]["summary"] = summary
                article_state[article_id]["Summarized"] = summary # For clustering logic
                article_state[article_id]["status"] = "completed"
            print(f"[Summarize] Done: {url}")
        except Exception as e:
            print(f"[Summarize Error] {url}: {e}")
            async with state_lock:
                article_state[article_id]["summary"] = title
                article_state[article_id]["Summarized"] = title
                article_state[article_id]["status"] = "completed"
        finally:
            summarize_queue.task_done()

async def telegram_worker(classify_queue):
    channels = load_current_channels()
    if not channels or not API_ID or not API_HASH:
        print("[Telegram] No active channels or API credentials found. Skipping Telegram.")
        return
        
    print(f"[Telegram] Fetching history from {len(channels)} channels...")
    try:
        client = TelegramClient('briefley_session', API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            print("[Telegram Error] Session not authorized. Please run telegram_ingestor.py to log in.")
            await client.disconnect()
            return
            
        for channel in channels:
            print(f"[Telegram] Fetching @{channel}...")
            try:
                messages = await client.get_messages(channel, limit=15)
                for msg in messages:
                    if msg.message and msg.message.strip():
                        article_id = generate_id(f"tg_{channel}_{msg.id}")
                        text = msg.message.strip()
                        
                        async with state_lock:
                            if article_id not in article_state:
                                article_state[article_id] = {
                                    "id": article_id,
                                    "url": f"https://t.me/{channel}/{msg.id}",
                                    "source_name": channel,
                                    "title": None,
                                    "image_url": None,
                                    "text": text,
                                    "category": None,
                                    "summary": text, # Bypass summarization
                                    "Summarized": text, # Bypass summarization
                                    "timestamp": msg.date.isoformat() if msg.date else datetime.datetime.now().isoformat(),
                                    "status": "pending_classification" # Means it skips scraping/summarizing
                                }
                        # Push straight to classify queue
                        await classify_queue.put(article_id)
            except Exception as e:
                print(f"[Telegram Error] Could not fetch @{channel}: {e}")
                
        await client.disconnect()
        print("[Telegram] Finished fetching all channels.")
    except Exception as e:
        print(f"[Telegram Fatal Error] {e}")

async def async_main():
    print("="*60)
    print("Starting Asynchronous Briefley Pipeline")
    print("="*60)
    
    start_time = time.time()
    
    # Create Queues
    feed_queue = asyncio.Queue()
    scrape_queue = asyncio.Queue()
    classify_queue = asyncio.Queue()
    summarize_queue = asyncio.Queue()
    
    # Configure Workers
    NUM_RSS_WORKERS = 3
    NUM_SCRAPE_WORKERS = 5
    NUM_CLASSIFY_WORKERS = 3
    NUM_SUMMARIZE_WORKERS = 2 # Strictly limited to 2 to prevent PyTorch/HuggingFace OOM
    
    workers = []
    
    # Start RSS workers
    for _ in range(NUM_RSS_WORKERS):
        workers.append(asyncio.create_task(rss_worker(feed_queue, scrape_queue)))
        
    # Start Scrape workers
    for _ in range(NUM_SCRAPE_WORKERS):
        workers.append(asyncio.create_task(scrape_worker(scrape_queue, classify_queue, summarize_queue)))
        
    # Start Classify workers
    for _ in range(NUM_CLASSIFY_WORKERS):
        workers.append(asyncio.create_task(classify_worker(classify_queue)))
        
    # Start Summarize workers
    for _ in range(NUM_SUMMARIZE_WORKERS):
        workers.append(asyncio.create_task(summarize_worker(summarize_queue)))
        
    # Load Feeds
    active_feeds = load_current_rss()
    if not active_feeds:
        print("No active RSS feeds configured. Exiting.")
        return
        
    for feed_name in active_feeds:
        if feed_name in AVAILABLE_RSS_FEEDS:
            rss_url = AVAILABLE_RSS_FEEDS[feed_name]
            await feed_queue.put((feed_name, rss_url))
            
    # Start Telegram Fetcher concurrently with RSS
    tg_task = asyncio.create_task(telegram_worker(classify_queue))
            
    # Wait for all queues to be fully processed
    print("[Pipeline] Waiting for all feeds to be fetched...")
    await feed_queue.join()
    
    print("[Pipeline] Waiting for all articles to be scraped...")
    await scrape_queue.join()
    
    print("[Pipeline] Waiting for all articles to be classified...")
    await classify_queue.join()
    
    print("[Pipeline] Waiting for all articles to be summarized...")
    await summarize_queue.join()
    
    print("[Pipeline] Waiting for Telegram fetcher to complete...")
    await tg_task
    
    # Wait one more time for classify queue in case Telegram messages arrived late
    await classify_queue.join()
    
    # Cancel all worker tasks since queues are empty
    for w in workers:
        w.cancel()
        
    # Filter only completed articles
    processed_articles = []
    async with state_lock:
        for article_id, data in article_state.items():
            if data["status"] in ["completed", "pending_classification"] and data["summary"]:
                data["video_url"] = None
                processed_articles.append(data)
                
    if not processed_articles:
        print("No articles successfully processed. Exiting.")
        return
        
    print(f"\\n[Pipeline] Proceeding to Clustering with {len(processed_articles)} articles.")
    
    # Sync operation: Clustering
    cluster_labels = clusters(processed_articles)
    for article in processed_articles:
        article["cluster_id"] = cluster_labels.get(article["id"], "-1")
        
    print(f"[Pipeline] Clustering complete. Found {len(set(cluster_labels.values()))} clusters.")
    
    # --- Post-clustering deduplication ---
    before_dedup = len(processed_articles)
    processed_articles = deduplicate_articles(processed_articles, threshold=0.90)
    duplicates_removed = before_dedup - len(processed_articles)
    print(f"[Dedup] Removed {duplicates_removed} near-duplicate article(s) "
          f"({before_dedup} -> {len(processed_articles)}).")
    
    # Sync operation: Vector DB Insertion
    print("[Pipeline] Connecting to Vector DB...")
    vdb = VectorDBHelper()
    embedder = get_embedder()
    
    inserted_count = 0
    for article in processed_articles:
        filtered_summary = remove_stopwords(article["summary"])
        embedding = embedder.encode(filtered_summary).tolist()
        
        payload = {
            "url": article["url"],
            "source_name": article["source_name"],
            "title": article["title"],
            "category": article["category"],
            "cluster_id": article["cluster_id"],
            "timestamp": article["timestamp"],
            "summary_text": article["summary"],
            "image_url": article["image_url"],
            "video_url": article["video_url"],
            "full_text": article["text"] 
        }
        
        success = vdb.upsert_article(
            article_id=article["id"],
            embedding=embedding,
            payload=payload
        )
        if success:
            inserted_count += 1
            
    print(f"\\n[Pipeline] Successfully inserted {inserted_count}/{len(processed_articles)} articles into Vector DB.")
    total_time = time.time() - start_time
    print(f"[Pipeline] Finished in {total_time:.2f} seconds.")

import io

if __name__ == "__main__":
    if sys.platform == 'win32':
        # Fix encoding issues in windows console
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(async_main())
