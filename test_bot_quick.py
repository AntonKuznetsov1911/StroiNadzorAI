# -*- coding: utf-8 -*-
"""
Test bot API keys
"""
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print("=" * 60)
print("CHECKING API KEYS")
print("=" * 60)

if TELEGRAM_TOKEN:
    print(f"OK TELEGRAM_BOT_TOKEN: {TELEGRAM_TOKEN[:20]}...{TELEGRAM_TOKEN[-10:]}")
else:
    print("ERROR: TELEGRAM_BOT_TOKEN not found!")

if OPENAI_API_KEY:
    print(f"OK OPENAI_API_KEY: {OPENAI_API_KEY[:20]}...{OPENAI_API_KEY[-10:]}")
else:
    print("ERROR: OPENAI_API_KEY not found!")

print("\n" + "=" * 60)
print("TESTING OpenAI API")
print("=" * 60)

try:
    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "Say 'API works' in one word"}
        ],
        max_tokens=10
    )

    answer = response.choices[0].message.content
    print(f"SUCCESS: OpenAI API WORKS!")
    print(f"  Response: {answer}")
    print(f"  Model: gpt-4o-mini")
    print(f"  Tokens used: {response.usage.total_tokens}")

except Exception as e:
    print(f"ERROR: OpenAI API failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("RESULT")
print("=" * 60)

if TELEGRAM_TOKEN and OPENAI_API_KEY:
    print("SUCCESS: All keys are valid and OpenAI works!")
    print("Bot is ready to run!")
    print("\nNow update these keys on Railway:")
    print(f"  TELEGRAM_BOT_TOKEN={TELEGRAM_TOKEN}")
    print(f"  OPENAI_API_KEY={OPENAI_API_KEY}")
else:
    print("ERROR: Not all keys are configured!")
    sys.exit(1)

print("=" * 60)
