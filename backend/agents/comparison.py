import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

COMPARISON_SYSTEM_PROMPT_DOCTOR = """You are the Comparison Agent in a clinical debate panel.
Your job is to compare a doctor's sealed diagnosis against the panel's final verdict.
BE EXTREMELY CONCISE. Each field is ONE short line only — no bullet lists, no elaboration, no paragraphs.

Always respond in this exact format:

DOCTOR'S DIAGNOSIS: [one line]
PANEL VERDICT: [one line]

AGREEMENT: [Yes / Partial / No]

WHERE THEY AGREED: [one line, max 15 words]

WHERE THEY DIVERGED: [one line, max 15 words]

WHAT THE DOCTOR MISSED: [one line, max 15 words]

WHAT THE DOCTOR GOT RIGHT: [one line, max 15 words]

CLOSEST SPECIALIST MATCH: [specialist name, one line]

SUMMARY: [ONE sentence only, max 20 words]"""


COMPARISON_SYSTEM_PROMPT_STUDENT = """You are the Comparison Agent in a clinical debate panel.
Your job is to compare a medical student's reasoning against the panel's final verdict.
Be educational and constructive, but BE EXTREMELY CONCISE. Each field is ONE short line only — no bullet lists, no elaboration.

Always respond in this exact format:

STUDENT'S DIAGNOSIS: [one line]
PANEL VERDICT: [one line]

AGREEMENT: [Yes / Partial / No]

WHAT YOU GOT RIGHT: [one line, max 15 words]

WHAT YOU MISSED: [one line, max 15 words]

REASONING QUALITY: [Strong / Adequate / Needs Improvement]

CLOSEST SPECIALIST MATCH: [specialist name, one line]

LEARNING POINTS: [one line, max 20 words, combine into a single takeaway]

OVERALL FEEDBACK: [ONE sentence only, max 20 words]"""


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
            max_tokens=300
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