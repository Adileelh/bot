import discord
import feedparser
import os
from dotenv import load_dotenv
import yaml
import asyncio
import threading

from fastapi import FastAPI
import uvicorn

load_dotenv()
intents = discord.Intents.all()
client = discord.Client(intents=intents)

FORUM_CHANNEL_ID = int(os.getenv('FORUM_CHANNEL_ID', 0))
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DISCORD_THREAD_IDS = [
    int(x.strip())
    for x in os.getenv('DISCORD_THREAD_IDS', '').split(',')
    if x.strip()
]

RSS_FEED_URLS = [
    x.strip()
    for x in os.getenv('RSS_FEED_URLS', '').split(',')
    if x.strip()
]
EMOJI = "\U0001F4F0"  # Newspaper emoji
sent_articles_file = "sent_articles.yaml"

print(dict(os.environ))


print("DEBUG ENV")
print("DISCORD_BOT_TOKEN:", DISCORD_BOT_TOKEN[:10] + "..." if DISCORD_BOT_TOKEN else None)
print("DISCORD_THREAD_IDS:", DISCORD_THREAD_IDS)
print("RSS_FEED_URLS:", RSS_FEED_URLS)

# FastAPI app
app = FastAPI()

@app.get("/")
def root():
    return {"message": "Bot is alive!"}

@app.get("/ping")
@app.head("/ping", include_in_schema=False)
def ping():
    return {"status": "ok"}

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000)

async def fetch_feed_for_thread_and_url(thread, rss_feed_url):
    print(f"[FETCH] Thread: {thread.id} / {getattr(thread, 'name', None)}\n[FETCH] RSS: {rss_feed_url}")

    if os.path.exists(sent_articles_file):
        with open(sent_articles_file, "r") as f:
            sent_articles = yaml.safe_load(f) or {}
    else:
        sent_articles = {}

    feed = feedparser.parse(rss_feed_url)
    if feed.bozo:
        print(f"Error parsing RSS feed: {feed.bozo_exception}")
        return

    if not feed.entries:
        print("[RSS] No entries found in the feed.")
        return

    last_entry = feed.entries[0]

    if thread.id not in sent_articles:
        sent_articles[thread.id] = []

    if last_entry.link not in sent_articles[thread.id]:
        article_title = last_entry.title
        article_link = last_entry.link
        print(f"[SEND] Sending article to thread {thread.id}: {article_title} ({article_link})")
        sent_articles[thread.id].append(last_entry.link)

        try:
            await thread.send(f"{EMOJI}  |  {article_title}\n\n{article_link}")
            print("[SEND] Article sent!")
        except Exception as e:
            print(f"Error sending message to thread {thread.id}: {e}")

    # Save state
    while True:
        try:
            with open(sent_articles_file, "w") as f:
                yaml.dump(sent_articles, f, default_flow_style=False, sort_keys=False)
            print("[YAML] State saved.")
            break
        except Exception as e:
            print(f"Error writing YAML: {e}")
            await asyncio.sleep(1)


@client.event
async def on_ready():
    print(f"Bot logged in as {client.user.name}")

    while True:
        for thread_id, feed_url in zip(DISCORD_THREAD_IDS, RSS_FEED_URLS):
            print(f"[LOOP] Trying thread_id={thread_id} with feed_url={feed_url[:80]}...")
            thread = client.get_channel(thread_id)
            if thread is not None:
                print(f"[LOOP] Got thread {thread_id}, launching fetch...")
                await fetch_feed_for_thread_and_url(thread, feed_url)
            else:
                print(f"[LOOP] Thread {thread_id} not found!")
        await asyncio.sleep(600)

if __name__ == "__main__":
    # Lancer FastAPI dans un thread séparé
    threading.Thread(target=run_fastapi, daemon=True).start()
    # Lancer le bot Discord
    print("Starting the bot...")
    client.run(DISCORD_BOT_TOKEN)
