import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CHAIR_SYSTEM_PROMPT = """You are the Chair of a clinical debate panel.
You have two responsibilities:

RESPONSIBILITY 1 — MODERATING INTERJECTIONS:
When a user interjects mid-debate, you decide which specialists need to re-evaluate
based on the new information. Route the interjection clearly.

RESPONSIBILITY 2 — FINAL VERDICT:
After all debate rounds are complete, synthesize all specialist arguments and deliver
a final structured verdict.

For the FINAL VERDICT always respond in this format:

FINAL DIAGNOSIS: [most likely diagnosis]

DIFFERENTIAL DIAGNOSES:
1. [diagnosis 1] - [confidence %]
2. [diagnosis 2] - [confidence %]
3. [diagnosis 3] - [confidence %]

KEY REASONING: [2-3 sentences summarizing why this diagnosis was reached]

RECOMMENDED NEXT STEPS: [immediate clinical actions]

PANEL CONSENSUS: [High / Moderate / Low — how much did specialists agree]

Be authoritative, clear, and clinically precise."""


INTERJECTION_PROMPT = """You are the Chair of a clinical debate panel.
A user has interjected mid-debate with new information.
Decide which specialists should re-evaluate based on this new information.
Respond in this format:

ACKNOWLEDGING INTERJECTION: [summarize what was added]
DIRECTING TO: [list which specialists should respond to this]
REASON: [why these specialists specifically]"""


def run_chair_verdict(case_text: str, debate_log: list) -> dict:
    """
    Chair synthesizes the full debate and delivers final verdict.
    Summarizes transcript to stay within token limits.
    """
    try:
        # Build condensed debate summary — one line per agent per round
        debate_summary = "\n\n".join([
            f"{r['agent_name'].upper()} (Round {r['round_number']}):\n{r['response'][:300]}..."
            for r in debate_log
        ])

        messages = [
            {"role": "system", "content": CHAIR_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""Patient Case:
{case_text}

Debate Summary (condensed):
{debate_summary}

Now deliver the final verdict."""
            }
        ]

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
            temperature=0.2,
            max_tokens=2000
        )

        return {
            "agent_name": "chair",
            "api_used": "groq",
            "response": response.choices[0].message.content.strip(),
            "confidence": 1.0,
            "round_number": 99
        }

    except Exception as e:
        return {
            "agent_name": "chair",
            "api_used": "groq",
            "response": f"Chair unavailable. Error: {str(e)}",
            "confidence": 0.0,
            "round_number": 99
        }

def run_chair_interjection(
    case_text: str,
    debate_log: list,
    interjection: str
) -> dict:
    """
    Chair handles a user interjection mid-debate.
    Returns which specialists should re-evaluate.
    """
    try:
        debate_transcript = "\n\n".join([
            f"{r['agent_name'].upper()}:\n{r['response']}"
            for r in debate_log
        ])

        messages = [
            {"role": "system", "content": INTERJECTION_PROMPT},
            {
                "role": "user",
                "content": f"""Patient Case:
{case_text}

Debate So Far:
{debate_transcript}

User Interjection:
{interjection}

How should this be routed?"""
            }
        ]

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
            temperature=0.2,
            max_tokens=1000
        )

        return {
            "agent_name": "chair",
            "api_used": "groq",
            "response": response.choices[0].message.content.strip(),
            "confidence": 1.0,
            "round_number": len(debate_log)
        }

    except Exception as e:
        return {
            "agent_name": "chair",
            "api_used": "groq",
            "response": f"Chair interjection handling failed. Error: {str(e)}",
            "confidence": 0.0,
            "round_number": len(debate_log)
        }