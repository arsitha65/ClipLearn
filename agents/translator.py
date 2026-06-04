from openai import OpenAI
import os
import json
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SUPPORTED_LANGUAGES = [
    "Spanish", "French", "German", "Chinese", "Japanese",
    "Arabic", "Hindi", "Portuguese", "Korean", "Italian"
]

def translate_content(content: dict, target_language: str) -> dict:
    """Agent 4 - Translator: Translate all study materials in one API call"""
    
    if target_language not in SUPPORTED_LANGUAGES:
        return {"success": False, "error": f"Language not supported. Choose from: {', '.join(SUPPORTED_LANGUAGES)}"}
    
    try:
        flashcards_input = [
            {"front": c["front"], "back": c["back"], "timestamp": c["timestamp"]}
            for c in content.get("flashcards", [])
        ]

        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=8000,
            messages=[{
                "role": "user",
                "content": f"""Translate the following study materials to {target_language}.

Rules:
- Keep all timestamps in MM:SS format unchanged
- Return ONLY valid JSON, nothing else
- No markdown, no backticks, no explanation

Input JSON:
{{
  "outline": {json.dumps(content.get("outline", ""))},
  "summary_90": {json.dumps(content.get("summary_90", ""))},
  "summary_5min": {json.dumps(content.get("summary_5min", ""))},
  "flashcards": {json.dumps(flashcards_input)}
}}

Return this exact structure translated to {target_language}:
{{
  "outline": "...",
  "summary_90": "...",
  "summary_5min": "...",
  "flashcards": [
    {{"front": "...", "back": "...", "timestamp": "MM:SS"}},
    ...
  ]
}}"""
            }]
        )

        raw = response.choices[0].message.content.strip()
        
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        translated = json.loads(raw)

        return {
            "success": True,
            "language": target_language,
            "outline": translated.get("outline", ""),
            "summary_90": translated.get("summary_90", ""),
            "summary_5min": translated.get("summary_5min", ""),
            "flashcards": translated.get("flashcards", [])
        }

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Translation parsing failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Translation failed: {str(e)}"}