import os
from groq import Groq
from dotenv import load_dotenv
import json

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

TRIAGE_SYSTEM_PROMPT = """You are a medical triage agent. Your only job is to assess the urgency of a patient case.
Analyze the case for red flag symptoms and vital sign abnormalities.
You must respond ONLY with valid JSON in this exact format, nothing else:
{
    "severity": "CRITICAL" or "URGENT" or "ROUTINE",
    "reason": "one line explanation"
}

CRITICAL = immediate danger to life (possible MI, stroke, sepsis, PE, severe trauma)
URGENT = needs attention within 24-48 hours
ROUTINE = standard follow-up, no immediate danger"""


def run_triage(case_text: str) -> dict:
    """
    Runs a fast blind triage check on the case.
    Returns severity level and reason.
    """
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                {"role": "user", "content": f"Assess this case: {case_text}"}
            ],
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"}
        )

        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)

        # Validate the response has required fields
        if "severity" not in result or "reason" not in result:
            raise ValueError("Invalid triage response format")

        # Ensure severity is one of the valid options
        if result["severity"] not in ["CRITICAL", "URGENT", "ROUTINE"]:
            result["severity"] = "URGENT"

        return result

    except json.JSONDecodeError:
        # If JSON parsing fails return URGENT as safe default
        return {
            "severity": "URGENT",
            "reason": "Triage assessment unavailable — defaulting to URGENT for safety"
        }

    except Exception as e:
        return {
            "severity": "URGENT",
            "reason": f"Triage service error — defaulting to URGENT for safety"
        }


def reconcile_with_user_flag(triage_result: dict, user_severity_flag: str = None) -> dict:
    """
    Reconciles triage result with user's stated concern.
    User input can only raise severity, never lower it.
    """
    severity_order = ["ROUTINE", "URGENT", "CRITICAL"]

    if user_severity_flag == "serious":
        current_index = severity_order.index(triage_result["severity"])
        # Bump up one level if user flagged as serious and not already CRITICAL
        if current_index < 2:
            triage_result["severity"] = severity_order[current_index + 1]
            triage_result["reason"] += " (elevated by user concern flag)"

    return triage_result