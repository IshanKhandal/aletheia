import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY_SKEPTIC"))

SKEPTIC_SYSTEM_PROMPT = """You are the Skeptic in a clinical debate panel.
Your job is NOT to diagnose — your job is to challenge every claim made by the other specialists.
Your responsibilities:
1. Identify any claims made without cited evidence or diagnostic criteria
2. Point out alternative diagnoses that were not considered
3. Flag any drug dosages, lab values, or clinical criteria that seem incorrect
4. Challenge overconfident conclusions
5. Ask hard questions that force specialists to justify their reasoning
Be direct, critical, and rigorous. Do not be polite about weak arguments.
If a claim has no cited source, say: "UNVERIFIED CLAIM: [the claim]"
If a diagnosis seems rushed, say: "INSUFFICIENT EVIDENCE FOR: [the diagnosis]"
End your response with a list of the top 2 weakest claims in the debate so far."""

def run_skeptic(case_text: str, debate_so_far: list) -> dict:
    """
    Skeptic reviews the single most recent specialist response and challenges it.
    Runs after every individual specialist opinion.
    """
    try:
        specialist_entries = [r for r in debate_so_far if r['agent_name'] != 'skeptic']
        if not specialist_entries:
            return {
                "agent_name": "skeptic",
                "api_used": "groq",
                "response": "No specialist opinion yet to review.",
                "confidence": 0.0,
                "round_number": len(debate_so_far)
            }
        latest = specialist_entries[-1]
        debate_transcript = f"{latest['agent_name'].upper()}:\n{latest['response'][:400]}"
        messages = [
            {"role": "system", "content": SKEPTIC_SYSTEM_PROMPT + "\n\nBE EXTREMELY BRIEF: 1-2 sentences maximum, no lists."},
            {
                "role": "user",
                "content": f"""Patient Case:
{case_text}
Latest specialist opinion to review:
{debate_transcript}
Challenge it in 1-2 sentences."""
            }
        ]
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
            temperature=0.3
        )
        return {
            "agent_name": "skeptic",
            "api_used": "groq",
            "response": response.choices[0].message.content.strip(),
            "confidence": 1.0,
            "round_number": len(debate_so_far)
        }
    except Exception as e:
        return {
            "agent_name": "skeptic",
            "api_used": "groq",
            "response": f"Skeptic unavailable — continuing debate without challenge. Error: {str(e)}",
            "confidence": 0.0,
            "round_number": len(debate_so_far)
        }