import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

PATIENT_SYSTEM_PROMPT = """You are simulating a real patient in a clinical training exercise.
You have a specific medical case file that contains your full history, symptoms, vitals, and test results.
However you will NOT volunteer this information freely.

Rules:
1. Only reveal information that the student directly and specifically asks about
2. If the question is vague, give a vague answer — like a real patient would
3. If the question is specific, give a specific accurate answer from your case file
4. Speak naturally as a patient — not in medical terminology
5. Show appropriate emotion — nervousness, pain, confusion
6. Never break character
7. Never reveal your full case file at once

Example:
Student asks: "How do you feel?"
You say: "Not great honestly, I've been really uncomfortable"

Student asks: "Where exactly is the pain and does it go anywhere?"
You say: "It's mainly in my chest, and yeah it kind of shoots down my left arm"

Stay in character at all times."""


def run_patient_agent(
    full_case_file: str,
    student_question: str,
    conversation_history: list = None
) -> dict:
    """
    Patient Agent responds to student questions.
    Only reveals information that is specifically asked for.
    full_case_file: the complete case details hidden from student
    student_question: what the student just asked
    conversation_history: list of previous Q&A exchanges
    """
    try:
        # Build conversation history for context
        messages = [
            {
                "role": "system",
                "content": f"{PATIENT_SYSTEM_PROMPT}\n\nYOUR CASE FILE (never reveal all at once):\n{full_case_file}"
            }
        ]

        # Add previous conversation history if exists
        if conversation_history:
            for exchange in conversation_history:
                messages.append({
                    "role": "user",
                    "content": exchange["question"]
                })
                messages.append({
                    "role": "assistant",
                    "content": exchange["answer"]
                })

        # Add current question
        messages.append({
            "role": "user",
            "content": student_question
        })

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )

        answer = response.choices[0].message.content.strip()

        return {
            "question": student_question,
            "answer": answer,
            "status": "ok"
        }

    except Exception as e:
        return {
            "question": student_question,
            "answer": "I'm sorry, I'm not feeling well enough to answer right now.",
            "status": f"error: {str(e)}"
        }


def compile_gathered_history(conversation_history: list) -> str:
    """
    Compiles all Q&A into a case summary to pass to the debate panel.
    This is what the student gathered — not the full hidden case file.
    """
    if not conversation_history:
        return "No history gathered by student."

    compiled = "HISTORY GATHERED BY STUDENT INTERVIEW:\n\n"
    for i, exchange in enumerate(conversation_history, 1):
        compiled += f"Q{i}: {exchange['question']}\n"
        compiled += f"A{i}: {exchange['answer']}\n\n"

    return compiled