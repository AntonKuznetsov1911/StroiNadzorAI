import sys
import traceback

print("Attempting to import bot...")
try:
    import bot
    print("Bot imported successfully!")
    print("Calling bot.main()...")
    bot.main()
except Exception as e:
    print(f"\n❌ ERROR: {e}\n")
    traceback.print_exc()
    sys.exit(1)
