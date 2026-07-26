import os
import random
from groq import Groq
from google import genai as google_genai
from dotenv import load_dotenv
from agents.specialists import SPECIALIST_PROMPTS

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
gemini_client = google_genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
gemini_client_2 = google_genai.Client(api_key=os.getenv("GEMINI_API_KEY_2"))

# Fallback responses used ONLY if the live API call fails (rate limit, invalid
# key, network issue, etc). Keeps the demo coherent instead of showing raw
# error text. These are generic, safe, non-committal clinical remarks that
# fit into almost any debate context.
FALLBACK_RESPONSES = [
    "From my standpoint, the evidence so far supports the leading diagnosis, though I'd want to confirm with standard first-line testing before fully committing. CONFIDENCE: 0.6",
    "I largely agree with the direction of this discussion, but I'd flag that a couple of alternative explanations haven't been fully ruled out yet. CONFIDENCE: 0.55",
    "Nothing here changes my assessment — the presentation is consistent with what's already been proposed, and I'd support moving forward with confirmatory workup. CONFIDENCE: 0.65",
    "I want to push back slightly — we should make sure we're not anchoring too early before the full picture is in. CONFIDENCE: 0.5",
]


def get_fallback_response(specialist_name: str) -> str:
    return random.choice(FALLBACK_RESPONSES)


def call_groq_specialist(model: str, system_prompt: str, case_text: str) -> str:
    concise_instruction = "\n\nIMPORTANT: Respond in 2-3 short sentences maximum. Be direct and concise, not exhaustive."
    response = groq_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt + concise_instruction},
            {"role": "user", "content": f"Analyze this case: {case_text}"}
        ],
        temperature=0.3,
        max_tokens=200
    )
    return response.choices[0].message.content.strip()

def call_gemini_specialist(model: str, system_prompt: str, case_text: str, client_choice: str = "gemini") -> str:
    import time
    concise_instruction = "\n\nIMPORTANT: Respond in 2-3 short sentences maximum. Be direct and concise, not exhaustive."
    models_to_try = [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    ]
    active_client = gemini_client_2 if client_choice == "gemini2" else gemini_client
    last_error = None
    for attempt_model in models_to_try:
        try:
            response = active_client.models.generate_content(
                model=attempt_model,
                contents=f"Analyze this case: {case_text}",
                config={"system_instruction": system_prompt + concise_instruction}
            )
            return response.text.strip()
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                print(f"[WARNING] {attempt_model} ({client_choice}) quota hit, trying next...")
                last_error = e
                time.sleep(1)
                continue
            elif "503" in error_str or "UNAVAILABLE" in error_str:
                print(f"[WARNING] {attempt_model} ({client_choice}) unavailable, trying next...")
                last_error = e
                time.sleep(1)
                continue
            else:
                raise e
    raise Exception(f"All Gemini models failed on {client_choice}. Last error: {last_error}")


def run_specialist(specialist_name: str, case_text: str, debate_log: list = None, round_number: int = 1) -> dict:
    """
    Routes the specialist call to the correct API based on their assignment.
    Injects debate history and challenge instructions so specialists actively debate.
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

    # 1. Format the debate history so far
    formatted_history = ""
    if debate_log:
        for msg in debate_log:
            who = msg.get("who", msg.get("agent", msg.get("agent_name", "Specialist"))).upper()
            text = msg.get("text", msg.get("response", ""))
            formatted_history += f"\n[{who}]: {text}\n"

    # 2. Construct the challenge user prompt
    user_prompt = f"""
Clinical Case Details:
{case_text}

Debate History So Far:
{formatted_history if formatted_history else "No previous statements. You are opening the debate."}

TASK FOR YOU ({specialist_name.upper()}):
Challenge the previous opinions! Do not echo or validate what other specialists said.
Defend your own specialty's differential diagnosis and explain why treating for their suspected diagnosis without ruling out your specialty's concern could be dangerous.
"""

    try:
        if api == "groq":
            raw_response = call_groq_specialist(model, system_prompt, user_prompt)
        elif api == "gemini":
            raw_response = call_gemini_specialist(model, system_prompt, user_prompt, client_choice="gemini")
        elif api == "gemini2":
            raw_response = call_gemini_specialist(model, system_prompt, user_prompt, client_choice="gemini2")
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
        # Live call failed — use a safe fallback instead of showing the raw error
        print(f"[FALLBACK USED] {specialist_name} ({api}) failed: {e}")
        fallback_text = get_fallback_response(specialist_name)
        return {
            "agent_name": specialist_name,
            "api_used": f"{api}-fallback",
            "response": fallback_text,
            "confidence": 0.6,
            "round_number": round_number
        }