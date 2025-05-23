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

# FastAPI app
app = FastAPI()

@app.get("/")
def root():
    return {"message": "Bot is alive!"}

@app.get("/ping")
def ping():
    return {"status": "ok"}

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000)

async def fetch_feed(channel):
    if os.path.exists(sent_articles_file):
        with open(sent_articles_file, "r") as f:
            sent_articles = yaml.safe_load(f)
    else:
        sent_articles = {}

    for rss_feed_url in RSS_FEED_URLS:
        feed = feedparser.parse(rss_feed_url)
        if feed.bozo:
            print(f"Error parsing RSS feed: {feed.bozo_exception}")
            continue

        last_entry = feed.entries[0]
        if channel.id not in sent_articles:
            sent_articles[channel.id] = []
        if last_entry.link not in sent_articles[channel.id]:
            article_title = last_entry.title
            article_link = last_entry.link
            sent_articles[channel.id].append(last_entry.link)
            try:
                await channel.send(f"{EMOJI}  |  {article_title}\n\n{article_link}")
            except Exception as e:
                print(f"Error sending message: {e}")

    while True:
        try:
            with open(sent_articles_file, "w") as f:
                yaml.dump(sent_articles, f, default_flow_style=False, sort_keys=False)
            break
        except Exception as e:
            print(f"Error writing YAML: {e}")
            await asyncio.sleep(1)

@client.event
async def on_ready():
    print(f"Bot logged in as {client.user.name}")

    while True:
        for channel_id in DISCORD_CHANNEL_IDS:
            channel = client.get_channel(channel_id)
            if channel is not None:
                await fetch_feed(channel)
        await asyncio.sleep(600)

if __name__ == "__main__":
    # Lancer FastAPI dans un thread séparé
    threading.Thread(target=run_fastapi, daemon=True).start()
    # Lancer le bot Discord
    print("Starting the bot...")
    client.run(DISCORD_BOT_TOKEN)
