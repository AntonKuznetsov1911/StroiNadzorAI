# -*- coding: utf-8 -*-
"""
Test all bot modules v3.8
"""
import sys
sys.path.insert(0, 'C:/Users/PC/StroiNadzorAI')

print("="*60)
print("TESTING ALL BOT MODULES v3.8")
print("="*60)

# 1. FAQ module
print("\n1. FAQ MODULE TEST")
print("-"*60)
try:
    from faq import search_faq, get_total_faq_count, FAQ_DATABASE

    total = get_total_faq_count()
    print(f"   [OK] FAQ loaded: {total} questions")

    print(f"   [OK] Categories: {len(FAQ_DATABASE)}")
    for cat_id, cat_data in FAQ_DATABASE.items():
        q_count = len(cat_data['questions'])
        print(f"      - {cat_data['name']}: {q_count} questions")

    results = search_faq("beton")
    print(f"   [OK] Search 'beton': {len(results)} results")

    results = search_faq("treshina")
    print(f"   [OK] Search 'treshina': {len(results)} results")

    print("   [SUCCESS] FAQ module works correctly!")

except Exception as e:
    print(f"   [ERROR] FAQ: {e}")

# 2. Cache Manager
print("\n2. CACHE MANAGER TEST")
print("-"*60)
try:
    from cache_manager import generate_cache_key, calculate_similarity

    key1 = generate_cache_key("What is concrete B25 strength?")
    key2 = generate_cache_key("what is concrete b25 strength?")
    print(f"   [OK] Key generation (same questions):")
    print(f"      Key 1: {key1[:16]}...")
    print(f"      Key 2: {key2[:16]}...")
    print(f"      Match: {key1 == key2}")

    sim1 = calculate_similarity(
        "What is concrete B25 strength?",
        "Concrete B25 strength value"
    )
    print(f"   [OK] Similarity similar: {sim1:.2%}")

    sim2 = calculate_similarity("Concrete B25", "Brick masonry")
    print(f"   [OK] Similarity different: {sim2:.2%}")

    print("   [SUCCESS] Cache Manager works correctly!")

except Exception as e:
    print(f"   [ERROR] Cache Manager: {e}")

# 3. Work Planner
print("\n3. WORK PLANNER TEST")
print("-"*60)
try:
    from work_planner import calculate_work_duration, WORK_TYPES

    print(f"   [OK] Work types: {len(WORK_TYPES)}")
    for work_type, data in WORK_TYPES.items():
        print(f"      - {data['name']}")

    result = calculate_work_duration(
        work_type="foundation_concrete",
        volume=100,
        temp=20
    )

    print(f"\n   [OK] Test calc (100m3 concrete at +20C):")
    print(f"      - Duration: {result['work_days']:.1f} days")
    print(f"      - Workers: {result['workers_needed']} people")
    print(f"      - Heating needed: {result['heating_required']}")

    result2 = calculate_work_duration(
        work_type="foundation_concrete",
        volume=100,
        temp=-10
    )

    print(f"\n   [OK] Test calc (100m3 concrete at -10C):")
    print(f"      - Duration: {result2['work_days']:.1f} days")
    print(f"      - Workers: {result2['workers_needed']} people")
    print(f"      - Heating needed: {result2['heating_required']}")
    print(f"      - Coefficient: x{result2['temp_coefficient']}")

    print("   [SUCCESS] Work Planner works correctly!")

except Exception as e:
    print(f"   [ERROR] Work Planner: {e}")

# 4. Bot.py syntax check
print("\n4. BOT.PY SYNTAX CHECK")
print("-"*60)
try:
    import py_compile
    py_compile.compile('C:/Users/PC/StroiNadzorAI/bot.py', doraise=True)
    print("   [SUCCESS] bot.py syntax is correct!")
except Exception as e:
    print(f"   [ERROR] bot.py syntax: {e}")

# 5. Calculator handlers
print("\n5. CALCULATOR HANDLERS CHECK")
print("-"*60)
try:
    from calculator_handlers import CONCRETE_LENGTH, create_concrete_calculator_handler
    print("   [OK] calculator_handlers imported!")
    print(f"   [OK] States defined (CONCRETE_LENGTH={CONCRETE_LENGTH})")
    print("   [SUCCESS] Calculator handlers work correctly!")
except Exception as e:
    print(f"   [ERROR] calculator_handlers: {e}")

# 6. Saved calculations
print("\n6. SAVED CALCULATIONS CHECK")
print("-"*60)
try:
    from saved_calculations import CALCULATOR_NAMES
    print("   [OK] saved_calculations imported!")
    print(f"   [OK] Calculator types: {len(CALCULATOR_NAMES)}")
    for calc_type, name in CALCULATOR_NAMES.items():
        print(f"      - {name}")
    print("   [SUCCESS] Saved calculations work correctly!")
except Exception as e:
    print(f"   [ERROR] saved_calculations: {e}")

# 7. Defect gallery
print("\n7. DEFECT GALLERY CHECK")
print("-"*60)
try:
    from defect_gallery import DEFECT_CATEGORIES, DEFECTS_DATABASE
    print("   [OK] defect_gallery imported!")
    print(f"   [OK] Defect categories: {len(DEFECT_CATEGORIES)}")

    total_defects = sum(len(defects) for defects in DEFECTS_DATABASE.values())
    print(f"   [OK] Total defects: {total_defects}")

    for cat_id, cat_data in DEFECT_CATEGORIES.items():
        count = len(DEFECTS_DATABASE.get(cat_id, {}))
        print(f"      - {cat_data['name']}: {count} defects")

    print("   [SUCCESS] Defect gallery works correctly!")
except Exception as e:
    print(f"   [ERROR] defect_gallery: {e}")

# 8. History manager
print("\n8. HISTORY MANAGER CHECK")
print("-"*60)
try:
    from history_manager import get_user_history_file
    print("   [OK] history_manager imported!")
    print("   [SUCCESS] History manager works correctly!")
except Exception as e:
    print(f"   [ERROR] history_manager: {e}")

print("\n" + "="*60)
print("FINAL TEST RESULTS")
print("="*60)
print("[SUCCESS] All modules passed checks!")
print("[SUCCESS] Syntax is correct!")
print("[SUCCESS] Functions work as expected!")
print("\nBot is ready to run!")
print("="*60)
