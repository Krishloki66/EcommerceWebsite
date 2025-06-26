import subprocess
import re
import os
import requests
import json
from bs4 import BeautifulSoup

OP_BASE_URL = "https://api.observepoint.com/v2"

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return result.stdout.strip() if result.stdout else ""
    except Exception as e:
        print(f"⚠️ Command failed: {cmd}\n{e}")
        return ""

def get_git_diff():
    print("🔄 Fetching origin/main...")
    run_cmd(["git", "fetch", "origin", "main"])
    print("🔍 Comparing latest commit on master vs origin/main...")
    return run_cmd(["git", "diff", "origin/main...HEAD"])

def extract_line_selectors(line):
    selectors = set()

    # HTML class and id attributes
    selectors.update(*[set(cls.split()) for cls in re.findall(r'class=["\']([^"\']+)["\']', line)])
    selectors.update(re.findall(r'id=["\']([^"\']+)["\']', line))

    # data-* attributes
    selectors.update(re.findall(r'data-[\w-]+=["\']([^"\']+)["\']', line))

    # JS DOM setAttribute
    for attr in ['class', 'id']:
        dom_matches = re.findall(rf'setAttribute\(["\']{attr}["\']\s*,\s*["\']([^"\']+)["\']\)', line)
        for match in dom_matches:
            selectors.update(match.split())

    # CSS selectors in stylesheets
    selectors.update(re.findall(r'\.([a-zA-Z0-9_-]+)\s*\{', line))
    selectors.update(re.findall(r'#([a-zA-Z0-9_-]+)\s*\{', line))

    return selectors

def extract_html_selectors(html_block):
    selectors = set()
    try:
        soup = BeautifulSoup(html_block, 'html.parser')
        for tag in soup.find_all(True):
            if tag.has_attr('class'):
                selectors.update(tag['class'])
            if tag.has_attr('id'):
                selectors.add(tag['id'])
            for attr, val in tag.attrs.items():
                if attr.startswith('data-') and isinstance(val, str):
                    selectors.add(val)
    except Exception as e:
        print(f"⚠️ HTML parse error: {e}")
    return selectors

def extract_selectors(diff_text):
    added_html_lines = []
    removed_html_lines = []
    added, removed = set(), set()

    for line in diff_text.splitlines():
        line = line.strip()
        if line.startswith('+') and not line.startswith('+++'):
            added_html_lines.append(line[1:])
            added.update(extract_line_selectors(line[1:]))
        elif line.startswith('-') and not line.startswith('---'):
            removed_html_lines.append(line[1:])
            removed.update(extract_line_selectors(line[1:]))

    # HTML-based extraction using BeautifulSoup
    added.update(extract_html_selectors("\n".join(added_html_lines)))
    removed.update(extract_html_selectors("\n".join(removed_html_lines)))

    return added - removed, removed - added

def ask_gemini(old_sel, new_sel, gemini_key):
    if not gemini_key:
        return "[Error] GEMINI_API_KEY not set."

    prompt = f"""We detected changes in selectors.
Removed: {', '.join(f'.{s}' for s in old_sel)}
Added: {', '.join(f'.{s}' for s in new_sel)}
Please suggest what UI elements were updated and how tests should be updated."""

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

    test_ids = [123456, 234567]  # Replace with actual ObservePoint test IDs

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

    print("🔐 GEMINI_API_KEY set:", bool(GEMINI_KEY))
    print("🔐 OP_API_KEY set:", bool(OP_API_KEY))

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

    suggestion = ask_gemini(removed, added, GEMINI_KEY)
    print("\n🤖 Gemini Suggestion:\n", suggestion)

    for old, new in zip(removed, added):
        update_observepoint_tests(old, new, OP_API_KEY)

if __name__ == "__main__":
    main()
