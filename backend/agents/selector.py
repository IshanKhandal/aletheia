import os
import json
from groq import Groq
from dotenv import load_dotenv
from agents.specialists import SPECIALIST_DESCRIPTIONS, SPECIALIST_PROMPTS

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Build the specialist list string for the selector prompt
SPECIALIST_LIST_TEXT = "\n".join([
    f"- {name}: {desc}"
    for name, desc in SPECIALIST_DESCRIPTIONS.items()
])

SELECTOR_SYSTEM_PROMPT = f"""You are a medical case router. Your only job is to select the 4 most relevant specialists for a given patient case.
Choose from this list:
{SPECIALIST_LIST_TEXT}

Rules:
1. Pick exactly 4 specialists
2. Choose based on the most likely diagnoses for the case
3. Respond ONLY with valid JSON in this exact format, nothing else:
{{
    "selected": ["specialist1", "specialist2", "specialist3", "specialist4"]
}}
Use only the exact specialist names from the list above."""


def check_api_diversity(selected: list) -> list:
    """
    No longer needed as an API-balancing constraint since all specialists
    now run on the same API. Kept as a pass-through for compatibility.
    """
    return selected[:4]


def run_selector(case_text: str, manual_specialists: list = None) -> dict:
    """
    Selects 4 specialists for the debate.
    If manual_specialists provided, validates and uses those.
    Otherwise uses AI to auto-select.
    """

    # Manual selection path
    if manual_specialists and len(manual_specialists) == 4:
        valid = [s for s in manual_specialists if s in SPECIALIST_PROMPTS]
        if len(valid) == 4:
            final = check_api_diversity(valid)
            return {
                "selected": final,
                "mode": "manual"
            }

    # Auto selection path
    # Auto selection path
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": SELECTOR_SYSTEM_PROMPT},
                {"role": "user", "content": f"Select specialists for this case: {case_text}"}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)

        selected = result.get("selected", [])

        # Validate all selected are real specialists
        valid = [s for s in selected if s in SPECIALIST_PROMPTS]

        # If less than 4 valid, fill with defaults
        defaults = ["cardiologist", "pulmonologist", "neurologist", "infectious_disease"]
        while len(valid) < 4:
            for d in defaults:
                if d not in valid:
                    valid.append(d)
                if len(valid) == 4:
                    break

        # Check API diversity
        final = check_api_diversity(valid[:4])

        return {
            "selected": final,
            "mode": "auto"
        }

    except Exception as e:
        # Default fallback panel
        print(f"SELECTOR FALLBACK TRIGGERED: {e}")
        return {
            "selected": ["cardiologist", "pulmonologist", "neurologist", "infectious_disease"],
            "mode": "fallback"
        }