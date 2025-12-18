# -*- coding: utf-8 -*-
"""
Send test message to bot and check response
IMPORTANT: You need to have a chat with the bot first!
"""
import os
import sys
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not found")
    sys.exit(1)

print("=" * 70)
print("TESTING BOT RESPONSE")
print("=" * 70)
print()

# Get bot username
print("Getting bot info...")
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"
response = requests.get(url)
data = response.json()

if not data.get("ok"):
    print(f"ERROR: {data.get('description')}")
    sys.exit(1)

bot_username = data["result"]["username"]
print(f"Bot: @{bot_username}")
print()

# Get your chat ID (from last message)
print("Looking for your chat ID...")
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
response = requests.get(url)
data = response.json()

if not data.get("ok"):
    print(f"ERROR: {data.get('description')}")
    sys.exit(1)

updates = data.get("result", [])

if not updates:
    print()
    print("=" * 70)
    print("NO MESSAGES FOUND")
    print("=" * 70)
    print()
    print("Please do this first:")
    print(f"1. Open Telegram")
    print(f"2. Find bot: @{bot_username}")
    print(f"3. Send: /start")
    print(f"4. Wait 5 seconds")
    print(f"5. Run this script again")
    print()
    sys.exit(0)

# Get the last chat
last_update = updates[-1]
chat_id = None

if "message" in last_update:
    chat_id = last_update["message"]["chat"]["id"]
    from_user = last_update["message"]["from"]
    print(f"Found chat with: {from_user.get('first_name')} (@{from_user.get('username', 'N/A')})")
elif "callback_query" in last_update:
    chat_id = last_update["callback_query"]["message"]["chat"]["id"]

if not chat_id:
    print("ERROR: Could not find chat ID")
    sys.exit(1)

print(f"Chat ID: {chat_id}")
print()

# Send test message
print("Sending test message to bot...")
test_message = "/start"
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
payload = {
    "chat_id": chat_id,
    "text": test_message
}

response = requests.post(url, json=payload)
data = response.json()

if data.get("ok"):
    print(f"SUCCESS: Test message sent!")
    print(f"Message: {test_message}")
else:
    print(f"ERROR: {data.get('description')}")
    sys.exit(1)

print()
print("Waiting for bot response (5 seconds)...")
time.sleep(5)

# Check for bot response
print("Checking bot response...")
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
response = requests.get(url)
data = response.json()

if data.get("ok"):
    updates = data.get("result", [])

    # Look for bot's response
    bot_responses = []
    for update in reversed(updates[-10:]):  # Check last 10 updates
        if "message" in update:
            msg = update["message"]
            if msg.get("from", {}).get("is_bot"):
                bot_responses.append(msg)

    if bot_responses:
        print()
        print("=" * 70)
        print("BOT IS RESPONDING!")
        print("=" * 70)
        print()
        latest = bot_responses[0]
        print(f"Bot response:")
        print(f"  {latest.get('text', '(photo or other media)')[:200]}")
        print()
        print("SUCCESS: Bot is working on Railway!")
        print()
    else:
        print()
        print("=" * 70)
        print("NO RESPONSE YET")
        print("=" * 70)
        print()
        print("Bot might still be starting up. Please:")
        print(f"1. Open Telegram and check @{bot_username}")
        print(f"2. Check if bot responded to /start")
        print(f"3. If yes - bot is working!")
        print(f"4. If no - check Railway logs")
        print()

else:
    print(f"ERROR: {data.get('description')}")

print("=" * 70)
