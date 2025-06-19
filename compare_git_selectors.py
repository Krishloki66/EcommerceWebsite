# compare_and_update.py
import subprocess, os, requests, re, json

GEMINI_KEY = os.getenv("AIzaSyDVKQGkVKwJpNmwIO3eHlgVp8Eb95nYhcs")
OBSERVEPOINT_KEY = os.getenv("bTVqbWcxM21nam5iM2dlOGZwNmxqMWFlZHUwOTdpbXBocm1sYWMwMjd2ZGQ4MW5xMXAyY2tza21tMCY3NDAzMiYxNzUwMjUwOTI3Mzc2")
OP_BASE_URL = "https://api.observepoint.com/v2"

def run_git_diff():
    result = subprocess.run(
        ["git", "diff", "origin/master..origin/main"],
        capture_output=True,
        text=True
    )
    return result.stdout if result.returncode == 0 else ""

def extract_selectors(diff):
    added, removed = set(), set()
    for line in diff.splitlines():
        if line.startswith("+") and 'class="' in line:
            added.update(re.findall(r'class="([^"]+)"', line))
        elif line.startswith("-") and 'class="' in line:
            removed.update(re.findall(r'class="([^"]+)"', line))
    return added, removed

def ask_gemini(old_sel, new_sel):
    prompt = f"""The following selectors were changed:
Old: {', '.join(f'.{x}' for x in old_sel)}
New: {', '.join(f'.{x}' for x in new_sel)}
Suggest what UI element changed and what to update in tests."""
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_KEY}",
        headers={"Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}]}
    )
    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"[Gemini Error] {e}"

def update_observepoint(selector_old, selector_new):
    # Simulated loop - you should map to actual ObservePoint test IDs
    test_ids = [12345, 23456]  # replace with real logic
    for tid in test_ids:
        data = {"selector": f".{selector_new}"}
        res = requests.patch(
            f"{OP_BASE_URL}/tag-tests/{tid}",
            headers={"Authorization": f"Token token={OBSERVEPOINT_KEY}", "Content-Type": "application/json"},
            json=data
        )
        print(f"Test {tid} updated with .{selector_new}: {res.status_code}")

def main():
    diff = run_git_diff()
    if not diff:
        print("❌ No diff found.")
        return

    added, removed = extract_selectors(diff)
    if not added and not removed:
        print("✅ No selector changes.")
        return

    print("➕ Added:", added)
    print("➖ Removed:", removed)

    explanation = ask_gemini(removed, added)
    print("\n🤖 Gemini Suggestion:\n", explanation)

    for old, new in zip(removed, added):  # basic pairing
        update_observepoint(old, new)

if __name__ == "__main__":
    main()
