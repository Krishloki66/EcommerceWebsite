import subprocess
import re
import os
import requests
import json

# Load API keys
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
OP_API_KEY = os.getenv("OP_API_KEY")
OP_BASE_URL = "https://api.observepoint.com/v2"

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return result.stdout.strip() if result.stdout else ""
    except Exception as e:
        print(f"⚠️ Command failed: {cmd}\n{e}")
        return ""

def get_git_diff():
    print("🔄 Fetching all remote branches...")
    run_cmd(["git", "fetch", "--all"])
    print("🔍 Checking diff between origin/master and origin/main...")
    return run_cmd(["git", "diff", "origin/master..origin/main"])

def extract_selectors(diff_text):
    added = set()
    removed = set()

    for line in diff_text.splitlines():
        line = line.strip()
        if line.startswith('+') and not line.startswith('+++'):
            added.update(re.findall(r'class="([^"]+)"', line))
            added.update(re.findall(r'id="([^"]+)"', line))
            added.update(re.findall(r'\.([a-zA-Z0-9_-]+)\s*\{', line))
            added.update(re.findall(r'#([a-zA-Z0-9_-]+)\s*\{', line))
        elif line.startswith('-') and not line.startswith('---'):
            removed.update(re.findall(r'class="([^"]+)"', line))
            removed.update(re.findall(r'id="([^"]+)"', line))
            removed.update(re.findall(r'\.([a-zA-Z0-9_-]+)\s*\{', line))
            removed.update(re.findall(r'#([a-zA-Z0-9_-]+)\s*\{', line))

    added = set(cls for entry in added for cls in entry.split())
    removed = set(cls for entry in removed for cls in entry.split())
    return added, removed

def ask_gemini(old_sel, new_sel):
    if not GEMINI_KEY:
        return "[Error] GEMINI_API_KEY not set."
    prompt = f"""We detected changes in selectors.
Removed: {', '.join(f'.{s}' for s in old_sel)}
Added: {', '.join(f'.{s}' for s in new_sel)}
Please suggest what UI elements were updated and how tests should be updated."""
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

def update_observepoint_tests(old_selector, new_selector):
    if not OP_API_KEY:
        print("❌ OP_API_KEY not set.")
        return

    # Example test IDs (replace with your actual ObservePoint journey/test IDs)
    test_ids = [123456, 234567]

    for tid in test_ids:
        payload = {
            "selector": f".{new_selector}"
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
            print(f"✅ Updated test {tid} with selector .{new_selector} | Status: {res.status_code}")
        except Exception as e:
            print(f"❌ Failed to update test {tid}: {e}")

def main():
    diff = get_git_diff()

    if not diff.strip():
        print("❌ No diff found or Git error.")
        return

    added, removed = extract_selectors(diff)

    if not added and not removed:
        print("✅ No selector changes found.")
        return

    print("➖ Removed selectors:", removed)
    print("➕ Added selectors:", added)

    suggestion = ask_gemini(removed, added)
    print("\n🤖 Gemini Suggestion:\n", suggestion)

    for old, new in zip(removed, added):
        update_observepoint_tests(old, new)

if __name__ == "__main__":
    main()
