import requests
from bs4 import BeautifulSoup
import json
import os

# Set your URLs here (old version and new version of the website)
old_url = "https://your-uhg-site.com/old-version"
new_url = "https://your-uhg-site.com/"

# Gemini API key (from GitHub Secrets)
GEMINI_API_KEY = os.getenv("AIzaSyCe770X9SaBrc93clrNiPm8ie266UQaT6M")
gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

# Extract selectors from given URL
def get_selectors(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    selectors = set()

    for tag in soup.find_all():
        if tag.has_attr('class'):
            for class_name in tag['class']:
                selectors.add(f".{class_name}")
        if tag.has_attr('id'):
            selectors.add(f"#{tag['id']}")

    return selectors

# Compare selectors between two versions
old_selectors = get_selectors(old_url)
new_selectors = get_selectors(new_url)

added = new_selectors - old_selectors
removed = old_selectors - new_selectors

selector_changes = []

# If there are any changes, explain them using Gemini
if added or removed:
    for sel in added:
        prompt = f"What does this selector mean and why might it have been added: {sel}"
        response = requests.post(
            f"{gemini_endpoint}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]}
        )
        explanation = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        selector_changes.append({
            "change": "added",
            "selector": sel,
            "explanation": explanation
        })

    for sel in removed:
        prompt = f"Why might this selector have been removed: {sel}"
        response = requests.post(
            f"{gemini_endpoint}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]}
        )
        explanation = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        selector_changes.append({
            "change": "removed",
            "selector": sel,
            "explanation": explanation
        })

    # Save to file
    with open("changes.json", "w") as f:
        json.dump(selector_changes, f, indent=2)

    # Print for GitHub Actions
    print("🟢 Selector changes detected:")
    print(json.dumps(selector_changes, indent=2))

else:
    print("✅ No selector changes detected between the two versions.")
