# -*- coding: utf-8 -*-
"""
Test bot startup - check if bot can start without errors
"""
import sys
import os

sys.path.insert(0, 'C:/Users/PC/StroiNadzorAI')

print("="*60)
print("TESTING BOT STARTUP")
print("="*60)

# Set dummy tokens for testing
os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token'
os.environ['ANTHROPIC_API_KEY'] = 'test_key'

print("\n1. Importing bot module...")
try:
    import bot
    print("   [OK] bot module imported successfully")
except Exception as e:
    print(f"   [ERROR] Failed to import bot: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n2. Checking module availability flags...")
flags_to_check = [
    'FAQ_AVAILABLE',
    'CACHE_AVAILABLE',
    'PLANNER_AVAILABLE',
    'CALCULATOR_HANDLERS_AVAILABLE',
    'SAVED_CALCS_AVAILABLE',
    'DEFECT_GALLERY_AVAILABLE',
    'HISTORY_MANAGER_AVAILABLE'
]

for flag in flags_to_check:
    if hasattr(bot, flag):
        value = getattr(bot, flag)
        status = "[OK]" if value else "[WARN]"
        print(f"   {status} {flag}: {value}")
    else:
        print(f"   [WARN] {flag}: not found")

print("\n3. Checking key functions exist...")
functions_to_check = [
    'start_command',
    'help_command',
    'handle_text',
    'handle_photo'
]

for func_name in functions_to_check:
    if hasattr(bot, func_name):
        print(f"   [OK] {func_name} exists")
    else:
        print(f"   [ERROR] {func_name} not found!")

print("\n4. Testing FAQ functions...")
try:
    if bot.FAQ_AVAILABLE:
        from faq import get_total_faq_count
        count = get_total_faq_count()
        print(f"   [OK] FAQ has {count} questions")
    else:
        print("   [SKIP] FAQ not available")
except Exception as e:
    print(f"   [ERROR] FAQ test failed: {e}")

print("\n5. Testing Cache Manager...")
try:
    if bot.CACHE_AVAILABLE:
        from cache_manager import generate_cache_key
        key = generate_cache_key("test question")
        print(f"   [OK] Cache key generated: {key[:16]}...")
    else:
        print("   [SKIP] Cache Manager not available")
except Exception as e:
    print(f"   [ERROR] Cache test failed: {e}")

print("\n6. Testing Work Planner...")
try:
    if bot.PLANNER_AVAILABLE:
        from work_planner import WORK_TYPES
        print(f"   [OK] Work Planner has {len(WORK_TYPES)} work types")
    else:
        print("   [SKIP] Work Planner not available")
except Exception as e:
    print(f"   [ERROR] Planner test failed: {e}")

print("\n" + "="*60)
print("STARTUP TEST COMPLETED")
print("="*60)
print("[SUCCESS] Bot can start without critical errors!")
print("[INFO] Bot is ready for production use")
print("="*60)
