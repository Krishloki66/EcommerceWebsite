import subprocess
import re
import os
import requests
import json

# Load your API keys from GitHub Actions secrets or .env
GEMINI_KEY = os.getenv("AIzaSyDVKQGkVKwJpNmwIO3eHlgVp8Eb95nYhcs")
OP_API_KEY = os.getenv("bTVqbWcxM21nam5iM2dlOGZwNmxqMWFlZHUwOTdpbXBocm1sYWMwMjd2ZGQ4MW5xMXAyY2tza21tMCY3NDAzMiYxNzUwMjUwOTI3Mzc2")
OP_BASE_URL = "https://api.observepoint.com/v2"

def run_cmd(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    return result.stdout.strip()

def get_git_diff():
    run_cmd(["git", "fetch", "--all"])
    return run_cmd(["git", "diff", "origin/master..origin/main"])

def extract_selectors(diff_text):
    added = set()
    removed = set()

    for line in diff_text.splitlines():
        line = line.strip()
        if line.startswith('+') and not line.startswith('+++'):
            added.update(re.findall(r'class="([^"]+)"', line))
            added.update(re.findall(r'id="([^"]+)"', line))
        elif line.startswith('-') and not line.startswith('---'):
            removed.update(re.findall(r'class="([^"]+)"', line))
            removed.update(re.findall(r'id="([^"]+)"', line))

    added = set(cls for entry in added for cls in entry.split())
    removed = set(cls for entry in removed for cls in entry.split())
    return added, removed
print("GEMINI_KEY set:", bool(GEMINI_KEY))
def ask_gemini(old_sel, new_sel):
    if not GEMINI_KEY:
        return "[Error] GEMINI_API_KEY not set."

    prompt = f"""We detected changes in selectors:
Removed: {', '.join(f'.{s}' for s in old_sel)}
Added: {', '.join(f'.{s}' for s in new_sel)}
What UI components were likely updated and how should tests be adjusted?
"""

    try:
        res = requests.post(
            f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [
                    {"parts": [{"text": prompt}]}
                ]
            }
        )
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"[Gemini Error] {e}"

def update_op_journeys(old, new):
    if not OP_API_KEY:
        print("❌ OP_API_KEY not set.")
        return

    test_ids = [123456, 234567]  # Replace with your real test IDs
    for tid in test_ids:
        payload = {
            "selector": f".{new}"
        }
        try:
            res = requests.patch(
                f"{OP_BASE_URL}/tag-tests/{tid}",
                headers={
                    "Authorization": f"Token token={OP_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            print(f"✅ Updated OP test {tid} with selector .{new} | Status: {res.status_code}")
        except Exception as e:
            print(f"❌ Failed to update OP test {tid}: {e}")

def main():
    diff = get_git_diff()
    if not diff:
        print("❌ No diff found.")
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
        update_op_journeys(old, new)

if __name__ == "__main__":
    main()
