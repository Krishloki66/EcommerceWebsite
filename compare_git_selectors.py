import subprocess
import os
import requests
import json
import re

GEMINI_API_KEY ="AIzaSyCe770X9SaBrc93clrNiPm8ie266UQaT6M"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

# Run Git diff to get changes in HTML/CSS
def get_git_diff():
    result = subprocess.run(["git", "diff", "HEAD~1", "HEAD"], capture_output=True, text=True)
    return result.stdout

# Extract class and id selectors from diff
def extract_selectors(diff_text):
    added = set()
    removed = set()
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added.update(re.findall(r'class="([^"]+)"', line))
            added.update(re.findall(r'id="([^"]+)"', line))
        elif line.startswith("-") and not line.startswith("---"):
            removed.update(re.findall(r'class="([^"]+)"', line))
            removed.update(re.findall(r'id="([^"]+)"', line))
    # Split multiple class names
    added = set(cls for entry in added for cls in entry.split())
    removed = set(cls for entry in removed for cls in entry.split())
    return added, removed

# Ask Gemini to explain the change
def ask_gemini(added, removed):
    prompt = f"""These selectors were changed in a website update:
Added: {', '.join(f'.{s}' for s in added)}
Removed: {', '.join(f'.{s}' for s in removed)}

Explain what these changes might indicate in terms of UI or functionality."""
    
    response = requests.post(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}",
        headers={"Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}]}
    )
    
    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"⚠️ Failed to get response: {e}"

# MAIN EXECUTION
diff = get_git_diff()
added, removed = extract_selectors(diff)

if not added and not removed:
    print("🧠 Detected selector changes:")
    print("➕ Added:", added)
    print("➖ Removed:", removed)

    explanation = ask_gemini(added, removed)
    print("\n Gemini Explanation:\n", explanation)
else:
    print("✅ No selector changes found in the last commit.")
