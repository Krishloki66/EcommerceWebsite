import subprocess
import os
import re
import requests
import json
from dotenv import load_dotenv

# ✅ Load .env environment variables
load_dotenv()

# ✅ Get API keys from environment
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
OBSERVEPOINT_KEY = os.getenv("OP_API_KEY")
OP_BASE_URL = "https://api.observepoint.com/v2"

def run_git_diff():
    try:
        subprocess.run(["git", "fetch", "origin"], check=True)
        result = subprocess.run(
            ["git", "diff", "origin/master..origin/main"],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        return result.stdout
    except Exception as e:
        print(f"❌ Git diff failed: {e}")
        return ""

def extract_selectors(diff):
    added, removed = set(), set()
    for line in diff.splitlines():
        line = line.strip()
        if line.startswith("+") and 'class="' in line:
            matches = re.findall(r'class="([^"]+)"', line)
            for match in matches:
                for cls in match.split():
                    if cls.isidentifier():
                        added.add(cls)
        elif line.startswith("-") and 'class="' in line:
            matches = re.findall(r'class="([^"]+)"', line)
            for match in matches:
                for cls in match.split():
                    if cls.isidentifier():
                        removed.add(cls)
    return added, removed

def ask_gemini(old_sel, new_sel):
    if not GEMINI_KEY:
        return "[Error] GEMINI_API_KEY not found."

    prompt = f"""The following selectors were changed:
Old: {', '.join(f'.{x}' for x in old_sel)}
New: {', '.join(f'.{x}' for x in new_sel)}
Suggest what UI element changed and what to update in tests."""

    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [
                    {"parts": [{"text": prompt}]}
                ]
            }
        )
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"[Gemini API Error] {e}"

def update_observepoint(selector_old, selector_new):
    if not OBSERVEPOINT_KEY:
        print("[Error] OP_API_KEY not found.")
        return

    test_ids = [12345, 23456]  # Replace with your real ObservePoint tag test IDs

    for tid in test_ids:
        data = {"selector": f".{selector_new}"}
        try:
            response = requests.patch(
                f"{OP_BASE_URL}/tag-tests/{tid}",
                headers={
                    "Authorization": f"Token token={OBSERVEPOINT_KEY}",
                    "Content-Type": "application/json"
                },
                json=data
            )
            print(f"✅ Updated test {tid} with .{selector_new} | Status: {response.status_code}")
        except Exception as e:
            print(f"❌ Failed to update test {tid}: {e}")

def main():
    diff = run_git_diff()
    if not diff:
        print("❌ No selector diff found.")
        return

    added, removed = extract_selectors(diff)
    if not added and not removed:
        print("✅ No selector changes found.")
        return

    print("➕ Added selectors:", added)
    print("➖ Removed selectors:", removed)

    explanation = ask_gemini(removed, added)
    print("\n🤖 Gemini Suggestion:\n", explanation)

    for old, new in zip(removed, added):
        update_observepoint(old, new)

if __name__ == "__main__":
    main()
