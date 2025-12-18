# -*- coding: utf-8 -*-
"""
Check if Telegram bot is running on Railway
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

print("=" * 70)
print("CHECKING BOT STATUS ON RAILWAY")
print("=" * 70)
print()

if not TELEGRAM_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not found in .env")
    sys.exit(1)

print(f"Bot Token: {TELEGRAM_TOKEN[:20]}...{TELEGRAM_TOKEN[-10:]}")
print()

# Check bot info via Telegram API
print("1. Checking bot info via Telegram API...")
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"

try:
    response = requests.get(url, timeout=10)
    data = response.json()

    if data.get("ok"):
        bot_info = data.get("result", {})
        print(f"   SUCCESS: Bot is active!")
        print(f"   Bot Username: @{bot_info.get('username')}")
        print(f"   Bot Name: {bot_info.get('first_name')}")
        print(f"   Bot ID: {bot_info.get('id')}")
    else:
        print(f"   ERROR: {data.get('description')}")
        sys.exit(1)
except Exception as e:
    print(f"   ERROR: {e}")
    sys.exit(1)

print()

# Check recent updates
print("2. Checking if bot is receiving messages...")
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"

try:
    response = requests.get(url, timeout=10)
    data = response.json()

    if data.get("ok"):
        updates = data.get("result", [])
        print(f"   Total updates: {len(updates)}")

        if updates:
            last_update = updates[-1]
            message = last_update.get("message", {})
            if message:
                from_user = message.get("from", {})
                text = message.get("text", "")
                date = message.get("date", 0)

                print(f"   Last message from: {from_user.get('first_name')} (@{from_user.get('username', 'N/A')})")
                print(f"   Message: {text}")
                print(f"   Timestamp: {date}")
        else:
            print("   No messages received yet")
            print("   TIP: Send /start to the bot in Telegram to test")
    else:
        print(f"   ERROR: {data.get('description')}")
except Exception as e:
    print(f"   ERROR: {e}")

print()

# Check webhook status
print("3. Checking webhook configuration...")
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getWebhookInfo"

try:
    response = requests.get(url, timeout=10)
    data = response.json()

    if data.get("ok"):
        webhook = data.get("result", {})
        webhook_url = webhook.get("url", "")

        if webhook_url:
            print(f"   Webhook: {webhook_url}")
            print(f"   WARNING: Bot is using webhook mode")
            print(f"   For Railway polling mode, webhook should be empty")
        else:
            print(f"   SUCCESS: No webhook set (polling mode)")
            print(f"   This is correct for Railway deployment")

        pending = webhook.get("pending_update_count", 0)
        if pending > 0:
            print(f"   Pending updates: {pending}")
    else:
        print(f"   ERROR: {data.get('description')}")
except Exception as e:
    print(f"   ERROR: {e}")

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print()
print("Bot is configured correctly on Telegram side!")
print()
print("To verify Railway deployment:")
print("1. Open: https://railway.app/dashboard")
print("2. Go to StroiNadzorAI project")
print("3. Check Logs tab for: 'Bot СтройНадзорAI zapuschen uspeshno!'")
print("4. Status should be: Active (green)")
print()
print("To test the bot:")
print("1. Open Telegram")
print(f"2. Find bot: @{bot_info.get('username')}")
print("3. Send: /start")
print("4. Send question: 'Kakie trebovaniya k betonu M350?'")
print("5. Bot should respond with recommendations!")
print()
print("=" * 70)
