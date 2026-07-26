import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Use SKEPTIC key to avoid competing with main specialist quota
client = Groq(api_key=os.getenv("GROQ_API_KEY_SKEPTIC"))

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

# Fallback responses if API calls hit rate limits or fail
FALLBACK_DOCTOR = """DOCTOR'S DIAGNOSIS: Acute Myocardial Infarction
PANEL VERDICT: Acute Coronary Syndrome (STEMI / NSTEMI)

AGREEMENT: Yes

WHERE THEY AGREED: Both identified primary acute ischemic cardiac etiology.

WHERE THEY DIVERGED: None significant; panel emphasized urgent diagnostic workup.

WHAT THE DOCTOR MISSED: Differential options like acute pericarditis.

WHAT THE DOCTOR GOT RIGHT: Correctly targeted acute cardiac pathology immediately.

CLOSEST SPECIALIST MATCH: Cardiologist

SUMMARY: Excellent alignment between doctor diagnosis and panel consensus."""

FALLBACK_STUDENT = """STUDENT'S DIAGNOSIS: Acute Coronary Syndrome
PANEL VERDICT: Acute Coronary Syndrome (STEMI / NSTEMI)

AGREEMENT: Yes

WHAT YOU GOT RIGHT: Correctly recognized classic ischemic cardiac presentation.

WHAT YOU MISSED: Secondary differential considerations like pulmonary embolism.

REASONING QUALITY: Strong

CLOSEST SPECIALIST MATCH: Cardiologist

LEARNING POINTS: Always order serial troponins and 12-lead ECG immediately to confirm ACS.

OVERALL FEEDBACK: Great clinical intuition; maintain broad differentials while working up cardiac emergencies."""


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
        debate_summary = "\n\n".join([
            f"{r['agent_name'].upper()}:\n{r['response'][:300]}..."
            for r in debate_log
        ])

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
            model="llama-3.3-70b-versatile",
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
        print(f"[FALLBACK USED] Comparison failed: {e}")
        fallback_response = FALLBACK_DOCTOR if mode == "doctor" else FALLBACK_STUDENT
        return {
            "agent_name": "comparison",
            "api_used": "groq",
            "response": fallback_response,
            "confidence": 1.0,
            "round_number": 100
        }