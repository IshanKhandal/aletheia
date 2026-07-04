import os
from groq import Groq
from google import genai as google_genai
from dotenv import load_dotenv
from agents.specialists import SPECIALIST_PROMPTS

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
gemini_client = google_genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def call_groq_specialist(model: str, system_prompt: str, case_text: str) -> str:
    response = groq_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this case: {case_text}"}
        ],
        temperature=0.3,
        max_tokens=1500
    )
    return response.choices[0].message.content.strip()

def call_gemini_specialist(model: str, system_prompt: str, case_text: str) -> str:
    import time
    # Try lite model first — separate quota, less likely to be exhausted
    models_to_try = [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    ]
    last_error = None
    for attempt_model in models_to_try:
        try:
            response = gemini_client.models.generate_content(
                model=attempt_model,
                contents=f"Analyze this case: {case_text}",
                config={"system_instruction": system_prompt}
            )
            return response.text.strip()
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                print(f"[WARNING] {attempt_model} quota hit, trying next...")
                last_error = e
                time.sleep(2)
                continue
            elif "503" in error_str or "UNAVAILABLE" in error_str:
                print(f"[WARNING] {attempt_model} unavailable, trying next...")
                last_error = e
                time.sleep(3)
                continue
            else:
                raise e
    raise Exception(f"All Gemini models failed. Last error: {last_error}")


def run_specialist(specialist_name: str, case_text: str, round_number: int = 1) -> dict:
    """
    Routes the specialist call to the correct API based on their assignment.
    """
    if specialist_name not in SPECIALIST_PROMPTS:
        return {
            "agent_name": specialist_name,
            "api_used": "unknown",
            "response": "Specialist not found in roster.",
            "confidence": 0.0,
            "round_number": round_number
        }

    specialist = SPECIALIST_PROMPTS[specialist_name]
    api = specialist["api"]
    model = specialist["model"]
    system_prompt = specialist["system_prompt"]

    try:
        if api == "groq":
            raw_response = call_groq_specialist(model, system_prompt, case_text)
        elif api == "gemini":
            raw_response = call_gemini_specialist(model, system_prompt, case_text)
        else:
            raise ValueError(f"Unknown API: {api}")

        # Extract confidence score if present
        confidence = 0.7  # default
        if "CONFIDENCE:" in raw_response:
            try:
                conf_text = raw_response.split("CONFIDENCE:")[-1].strip()
                confidence = float(conf_text.split()[0])
            except (ValueError, IndexError):
                confidence = 0.7

        return {
            "agent_name": specialist_name,
            "api_used": api,
            "response": raw_response,
            "confidence": confidence,
            "round_number": round_number
        }

    except Exception as e:
        return {
            "agent_name": specialist_name,
            "api_used": api,
            "response": f"{specialist_name} unavailable. Error: {str(e)}",
            "confidence": 0.0,
            "round_number": round_number
        }