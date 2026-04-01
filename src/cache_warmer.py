import os
import sys
import time
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))

from generator import generate_lesson_plan
from config import DEFAULT_MODEL

# Define some high-traffic mock inputs
WARMUP_TASKS = [
    {
        "grade_level": "Grade 7",
        "subject": "Science",
        "topic": "Photosynthesis",
        "language": "English",
        "curriculum_version": "MATATAG Pilot"
    },
    {
        "grade_level": "Grade 4",
        "subject": "Mathematics",
        "topic": "Adding Fractions",
        "language": "English",
        "curriculum_version": "K-12 Standard"
    },
    {
        "grade_level": "Grade 10",
        "subject": "Araling Panlipunan (Social Studies)",
        "topic": "Kontemporaryong Isyu",
        "language": "Filipino",
        "curriculum_version": "K-12 Standard"
    }
]

def warm_cache():
    print("🚀 Starting EduPlan Cache Warmer...")
    load_dotenv()
    
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found in environment. Exiting.")
        return
        
    success_count = 0
    
    for i, task in enumerate(WARMUP_TASKS):
        print(f"[{i+1}/{len(WARMUP_TASKS)}] Generating: {task['grade_level']} - {task['subject']} - {task['topic']}...")
        
        start = time.time()
        result = generate_lesson_plan(
            grade_level=task["grade_level"],
            subject=task["subject"],
            topic=task["topic"],
            language=task["language"],
            additional_notes="",
            api_key=api_key,
            model=DEFAULT_MODEL,
            curriculum_version=task["curriculum_version"]
        )
        latency = time.time() - start
        
        # Check if we triggered a cache miss (actual generation) or hit
        if result.get("success"):
            if result.get("_served_from_cache"):
                print(f"   ⚡ Already cached. Skipped in {latency:.2f}s.")
            else:
                print(f"   ✅ Generated and stored in cache in {latency:.2f}s.")
                success_count += 1
        else:
            print(f"   ❌ Failed: {result.get('error')}")

    print(f"\n🎉 Cache warming complete. Added {success_count} new entries to local SQLite storage.")

if __name__ == "__main__":
    warm_cache()
