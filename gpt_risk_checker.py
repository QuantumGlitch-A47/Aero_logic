# gpt_risk_detector.py

import requests

# Known danger indicators
danger_indicators = [
    "switching sounds",
    "tense discussions",
    "uncoordinated decisions",
    "abnormal voice tone",
    "Where are we?",
    "I can’t see",
    "repeated alerts",
    "ignoring callouts",
    "long silence",
    "mental confusion",
    "shouting or threats",
    "fire", "smoke"
]

# Function to analyze transcript using GPT
def analyze_risk_with_gpt(transcript):
    api_key = ""

    prompt = f"""
You are an aviation safety assistant. Based on the transcript below, identify whether any critical danger indicators are present.

Transcript:
\"\"\"{transcript}\"\"\"

Known danger indicators include:
- {", ".join(danger_indicators)}

If any indicator is present, respond with:
- WARNING: Potential for catastrophe
- Risk Level: HIGH
- Detected Indicator(s): list them
- Recommendation: write 1-2 sentences with urgent action.

If no indicator is found, respond with:
- Status: Clear
- Risk Level: Low
- Reason: No critical phrases detected.

Respond only in English. Return plain text.
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "openai/gpt-4o",
        "max_tokens": 500,
        "messages": [
            {"role": "system", "content": "You are a professional aviation safety analyst."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        result = response.json() 
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Error contacting GPT: {str(e)}"
       






 
