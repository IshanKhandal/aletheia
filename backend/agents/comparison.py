import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

COMPARISON_SYSTEM_PROMPT_DOCTOR = """You are the Comparison Agent in a clinical debate panel.
Your job is to compare a doctor's sealed diagnosis against the panel's final verdict.

Always respond in this exact format:

DOCTOR'S DIAGNOSIS: [what the doctor submitted]
PANEL VERDICT: [what the panel concluded]

AGREEMENT: [Yes / Partial / No]

WHERE THEY AGREED:
- [point 1]
- [point 2]

WHERE THEY DIVERGED:
- [point 1]
- [point 2]

WHAT THE DOCTOR MISSED:
- [missed consideration 1]
- [missed consideration 2]

WHAT THE DOCTOR GOT RIGHT:
- [correct reasoning 1]

CLOSEST SPECIALIST MATCH: [which specialist's reasoning most closely matched the doctor's]

SUMMARY: [2-3 sentence honest assessment of the doctor's diagnostic reasoning]"""


COMPARISON_SYSTEM_PROMPT_STUDENT = """You are the Comparison Agent in a clinical debate panel.
Your job is to compare a medical student's reasoning against the panel's final verdict.
Be educational, constructive, and specific.

Always respond in this exact format:

STUDENT'S DIAGNOSIS: [what the student submitted]
PANEL VERDICT: [what the panel concluded]

AGREEMENT: [Yes / Partial / No]

WHAT YOU GOT RIGHT:
- [correct reasoning 1]
- [correct reasoning 2]

WHAT YOU MISSED:
- [missed consideration 1]
- [missed consideration 2]

REASONING QUALITY: [Strong / Adequate / Needs Improvement]

CLOSEST SPECIALIST MATCH: [which specialist's reasoning most closely matched the student's]

LEARNING POINTS:
- [key learning point 1]
- [key learning point 2]
- [key learning point 3]

OVERALL FEEDBACK: [2-3 sentence constructive assessment for the student]"""


def run_comparison(
    user_diagnosis: str,
    panel_verdict: str,
    debate_log: list,
    mode: str = "doctor",
    interjection_log: list = None
) -> dict:
    """
    Unseals user diagnosis and compares against panel verdict.
    mode: "doctor" or "student"
    """
    try:
        # Build debate summary
        debate_summary = "\n\n".join([
            f"{r['agent_name'].upper()}:\n{r['response'][:300]}..."
            for r in debate_log
        ])
        # Add interjection note if user interjected
        interjection_note = ""
        if interjection_log and len(interjection_log) > 0:
            interjection_note = f"\n\nNOTE: User interjected during debate with: {'; '.join(interjection_log)}"

        system_prompt = (
            COMPARISON_SYSTEM_PROMPT_DOCTOR
            if mode == "doctor"
            else COMPARISON_SYSTEM_PROMPT_STUDENT
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""User's Sealed Diagnosis:
{user_diagnosis}

Panel Final Verdict:
{panel_verdict}

Full Debate Transcript:
{debate_summary}
{interjection_note}

Now run the comparison."""
            }
        ]

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
            temperature=0.2,
            max_tokens=800
        )

        return {
            "agent_name": "comparison",
            "api_used": "groq",
            "response": response.choices[0].message.content.strip(),
            "confidence": 1.0,
            "round_number": 100
        }

    except Exception as e:
        return {
            "agent_name": "comparison",
            "api_used": "groq",
            "response": f"Comparison agent unavailable. Error: {str(e)}",
            "confidence": 0.0,
            "round_number": 100
        }