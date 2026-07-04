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
    Ensures no more than 2 specialists from the same API.
    Swaps out duplicates if needed.
    """
    api_counts = {}
    final_selected = []
    swapped = []

    for name in selected:
        api = SPECIALIST_PROMPTS[name]["api"]
        api_counts[api] = api_counts.get(api, 0) + 1
        if api_counts[api] <= 2:
            final_selected.append(name)
        else:
            swapped.append(name)

    # If we had to remove any, fill from remaining specialists
    if swapped:
        all_specialists = list(SPECIALIST_PROMPTS.keys())
        for specialist in all_specialists:
            if specialist not in final_selected and len(final_selected) < 4:
                api = SPECIALIST_PROMPTS[specialist]["api"]
                current_count = sum(
                    1 for s in final_selected
                    if SPECIALIST_PROMPTS[s]["api"] == api
                )
                if current_count < 2:
                    final_selected.append(specialist)

    return final_selected[:4]


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
    try:
        from google import genai as google_genai
        import os
        gemini_client = google_genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        gemini_response = gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=f"Select specialists for this case: {case_text}",
            config={
                "system_instruction": SELECTOR_SYSTEM_PROMPT,
                "response_mime_type": "application/json"
            }
        )
        raw = gemini_response.text.strip()
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