import subprocess
import re
import os
import requests
import json

OP_BASE_URL = "https://api.observepoint.com/v2"

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return result.stdout.strip() if result.stdout else ""
    except Exception as e:
        print(f"⚠️ Command failed: {cmd}\n{e}")
        return ""

def get_git_diff():
    print("🔄 Comparing origin/master with origin/main...")
    run_cmd(["git", "fetch", "--all"])
    return run_cmd(["git", "diff", "origin/master..origin/main"])

def extract_line_selectors(line):
    selectors = set()

    # HTML: class and id attributes
    selectors.update(re.findall(r'class=["\']([^"\']+)["\']', line))
    selectors.update(re.findall(r'id=["\']([^"\']+)["\']', line))

    # HTML: data-* attributes
    selectors.update(re.findall(r'data-[a-zA-Z0-9_-]+=["\']([^"\']+)["\']', line))

    # CSS: class and id selectors
    selectors.update(re.findall(r'\.([a-zA-Z0-9_-]+)\s*\{', line))
    selectors.update(re.findall(r'#([a-zA-Z0-9_-]+)\s*\{', line))

    # DOM changes via JS
    selectors.update(re.findall(r'setAttribute\(\s*[\'"]class[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]\s*\)', line))
    selectors.update(re.findall(r'setAttribute\(\s*[\'"]id[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]\s*\)', line))

    # Flatten class lists
    return set(cls for entry in selectors for cls in entry.split())

def extract_selectors(diff_text):
    added = set()
    removed = set()

    for line in diff_text.splitlines():
        line = line.strip()

        if line.startswith("+++ ") or line.startswith("--- "):
            continue

        if line.startswith('+') and not line.startswith('+++'):
            added.update(extract_line_selectors(line[1:]))
        elif line.startswith('-') and not line.startswith('---'):
            removed.update(extract_line_selectors(line[1:]))

    # Deduplicate any overlapping selectors (sometimes moved)
    final_added = added - removed
    final_removed = removed - added

    return final_added, final_removed

def ask_gemini(old_sel, new_sel, gemini_key):
    if not gemini_key:
        return "[Error] GEMINI_API_KEY not set."

    prompt = f"""We detected changes in UI selectors between branches.
Removed: {', '.join(sorted(old_sel)) if old_sel else 'None'}
Added: {', '.join(sorted(new_sel)) if new_sel else 'None'}
Please describe what UI changes happened and how automated tests should be updated."""

    try:
        res = requests.post(
            f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={gemini_key}",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]}
        )
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"[Gemini Error] {e}"

def update_observepoint_tests(old_selector, new_selector, op_api_key):
    if not op_api_key:
        print("❌ OP_API_KEY not set.")
        return

    test_ids = [123456, 234567]  # Replace with your real test IDs

    for tid in test_ids:
        payload = {
            "selector": f".{new_selector}"
        }
        try:
            res = requests.patch(
                f"{OP_BASE_URL}/tag-tests/{tid}",
                headers={
                    "Authorization": f"Token token={op_api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            print(f"✅ Updated test {tid} with selector .{new_selector} | Status: {res.status_code}")
        except Exception as e:
            print(f"❌ Failed to update test {tid}: {e}")

def main():
    GEMINI_KEY = os.getenv("GEMINI_API_KEY")
    OP_API_KEY = os.getenv("OP_API_KEY")

    print("🔐 GEMINI_KEY set:", bool(GEMINI_KEY))
    print("🔐 OP_API_KEY set:", bool(OP_API_KEY))

    diff = get_git_diff()

    if not diff.strip():
        print("❌ No diff found or Git error.")
        return

    added, removed = extract_selectors(diff)

    if not added and not removed:
        print("✅ No selector changes detected.")
        return

    print(f"➕ Added selectors: {sorted(added)}")
    print(f"➖ Removed selectors: {sorted(removed)}")

    suggestion = ask_gemini(removed, added, GEMINI_KEY)
    print("\n🤖 Gemini Suggestion:\n", suggestion)

    for old, new in zip(sorted(removed), sorted(added)):
        update_observepoint_tests(old, new, OP_API_KEY)

if __name__ == "__main__":
    main()
