import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_CHARS  = 8000


def truncate_transcript(transcript: str, max_chars: int = MAX_CHARS) -> str:
    if len(transcript) <= max_chars:
        return transcript
    print(f"[INFO] Transcript truncated: {len(transcript)} → {max_chars} chars")
    return transcript[:max_chars] + "\n...[truncated]"


def extract_json(text: str) -> dict:
    text = re.sub(r'```json', '', text)
    text = re.sub(r'```', '', text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    print("[WARN] JSON parse failed. Using raw text as summary.")
    return {
        "summary": text[:400] if text else "Summary unavailable.",
        "action_items": [],
        "decisions": []
    }


def summarize_transcript(transcript: str) -> dict:
    if not transcript or len(transcript.strip()) < 30:
        return {
            'summary': 'Transcript too short to summarize.',
            'action_items': '[]',
            'decisions': '[]'
        }

    trimmed = truncate_transcript(transcript)

    prompt = f"""Analyze this meeting transcript carefully. Return ONLY a valid JSON object with no extra text.

Required JSON format:
{{
  "summary": "2-3 sentence summary of the meeting covering the main topic, key discussions, and outcome",
  "action_items": ["Person A will do X by date", "Person B will do Y"],
  "decisions": ["Decision 1 made", "Decision 2 made"]
}}

Rules for extraction:
- For summary: cover WHO met, WHAT was discussed, and WHAT was concluded
- For action_items: extract ALL of the following:
    * Explicitly assigned tasks ("David, could you look for...")
    * Suggested actions that were agreed upon by the group
    * Follow-up items mentioned by any speaker
    * Anything someone volunteered or was asked to do
- For decisions: extract ALL of the following:
    * Formally agreed decisions
    * Conclusions the group reached
    * Approaches or directions the group agreed to take
- If a person's name is mentioned with a task, always include their name
- If no action items or decisions are found, use empty arrays []
- Do NOT include markdown, explanation, or any text outside the JSON

TRANSCRIPT:
{trimmed}"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.2,
        )
        raw = response.choices[0].message.content
        result = extract_json(raw)
        return {
            'summary': result.get('summary', 'No summary generated.'),
            'action_items': json.dumps(result.get('action_items', [])),
            'decisions': json.dumps(result.get('decisions', []))
        }

    except Exception as e:
        print(f"[ERROR] Summarization failed: {e}")
        return {
            'summary': f'Summarization failed: {str(e)[:120]}',
            'action_items': '[]',
            'decisions': '[]'
        }