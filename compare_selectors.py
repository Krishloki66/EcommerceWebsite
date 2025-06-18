import requests
import json
from bs4 import BeautifulSoup

# Replace with your real URLs (old and new deployments)
OLD_URL = "https://example.com/version1"
NEW_URL = "https://example.com/version2"
GEMINI_API_KEY = "AIzaSyCe770X9SaBrc93clrNiPm8ie266UQaT6M"  # Replace or use environment variable

def extract_selectors(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    selectors = []

    for el in soup.find_all(True):
        tag = el.name
        id_ = el.get('id', '')
        class_ = ' '.join(el.get('class', []))
        selectors.append({'tag': tag, 'id': id_, 'class': class_})
    
    return selectors

def call_gemini_api(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    output = response.json()
    try:
        return output["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "No explanation from Gemini."

def compare_and_explain(old_selectors, new_selectors):
    changes = []

    for old in old_selectors:
        for new in new_selectors:
            if old["tag"] == new["tag"] and old["id"] != new["id"]:
                old_sel = f'{old["tag"]}#{old["id"]}.{old["class"]}'
                new_sel = f'{new["tag"]}#{new["id"]}.{new["class"]}'
                prompt = f"Explain the difference between these two selectors:\nOld: {old_sel}\nNew: {new_sel}"
                explanation = call_gemini_api(prompt)
                changes.append({
                    "oldSelector": old_sel,
                    "newSelector": new_sel,
                    "explanation": explanation
                })
                break

    return changes

def main():
    old = extract_selectors(OLD_URL)
    new = extract_selectors(NEW_URL)
    changes = compare_and_explain(old, new)
    with open("changes.json", "w") as f:
        json.dump(changes, f, indent=2)
    print("Selector changes saved to changes.json")

if __name__ == "__main__":
    main()
