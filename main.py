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

DISCORD_CHANNEL_IDS = list(map(int, os.getenv('DISCORD_CHANNEL_IDS').split(',')))
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
RSS_FEED_URLS = os.getenv('RSS_FEED_URLS').split(",")
EMOJI = "\U0001F4F0"  # Newspaper emoji
sent_articles_file = "sent_articles.yaml"

print(dict(os.environ))


print("DEBUG ENV")
print("DISCORD_BOT_TOKEN:", DISCORD_BOT_TOKEN[:10] + "..." if DISCORD_BOT_TOKEN else None)
print("DISCORD_CHANNEL_IDS:", DISCORD_CHANNEL_IDS)
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

async def fetch_feed_for_channel_and_url(channel, rss_feed_url):
    print(f"\n---\n[FETCH] Channel: {channel.id} / {getattr(channel, 'name', None)}\n[FETCH] RSS: {rss_feed_url}")

    if os.path.exists(sent_articles_file):
        with open(sent_articles_file, "r") as f:
            sent_articles = yaml.safe_load(f)
            print(f"[YAML] Loaded {len(sent_articles.get(channel.id, [])) if sent_articles else 0} articles for channel {channel.id}")

    else:
        sent_articles = {}
        print("[YAML] No sent_articles.yaml file found, starting fresh.")

    feed = feedparser.parse(rss_feed_url)
    if feed.bozo:
        print(f"Error parsing RSS feed: {feed.bozo_exception}")
        return

    if not feed.entries:
        return

    print(f"[RSS] {len(feed.entries)} entries found. Showing the first 2:")
    for entry in feed.entries[:2]:
        print(f"    - {entry.title} ({entry.link})")

    last_entry = feed.entries[0]

    if channel.id not in sent_articles:
        sent_articles[channel.id] = []

    if last_entry.link not in sent_articles[channel.id]:
        article_title = last_entry.title
        article_link = last_entry.link
        print(f"[SEND] Sending article: {article_title} ({article_link})")
        sent_articles[channel.id].append(last_entry.link)

        try:
            await channel.send(f"{EMOJI}  |  {article_title}\n\n{article_link}")
            print("[SEND] Article sent!")

        except Exception as e:
            print(f"Error sending message: {e}")

    # Enregistre l'état
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
        for channel_id, feed_url in zip(DISCORD_CHANNEL_IDS, RSS_FEED_URLS):
            channel = client.get_channel(channel_id)
            if channel is not None:
                await fetch_feed_for_channel_and_url(channel, feed_url)
        await asyncio.sleep(600)

if __name__ == "__main__":
    # Lancer FastAPI dans un thread séparé
    threading.Thread(target=run_fastapi, daemon=True).start()
    # Lancer le bot Discord
    print("Starting the bot...")
    client.run(DISCORD_BOT_TOKEN)
