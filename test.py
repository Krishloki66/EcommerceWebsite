import requests
import json

GEMINI_API_KEY = "AIzaSyDVKQGkVKwJpNmwIO3eHlgVp8Eb95nYhcs"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContentt"

prompt = "What is the purpose of a `.btn-primary` selector in CSS?"

response = requests.post(
    f"{GEMINI_URL}?key={GEMINI_API_KEY}",
    headers={"Content-Type": "application/json"},
    json={"contents": [{"parts": [{"text": prompt}]}]}
)

print(json.dumps(response.json(), indent=2))
