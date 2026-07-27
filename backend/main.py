from db import get_similar_cases
import asyncio
import json
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Aletheia API", version="1.0.0")

# Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────
# REQUEST/RESPONSE MODELS
# ─────────────────────────────────────────

class CaseSubmission(BaseModel):
    case_text: str
    user_diagnosis: str
    severity_flag: Optional[str] = None
    mode: str = "doctor"
    manual_specialists: Optional[List[str]] = None

class PatientQueryRequest(BaseModel):
    case_text: str
    question: str
    history: Optional[List[dict]] = []

@app.post("/patient/respond")
async def patient_respond(request: PatientQueryRequest):
    """
    Roleplays as the patient based strictly on the case_text clinical vignette.
    """
    from groq import Groq
    import os

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ [PATIENT ERROR]: GROQ_API_KEY is missing from environment variables!")
        return {"response": "I'm having trouble thinking right now (API Key Missing)."}

    client = Groq(api_key=api_key)

    system_prompt = f"""You are a patient being interviewed by a medical student in an emergency setting.
You only know what is described in your medical case details below.
- Speak in first-person, layperson language (do NOT use advanced medical jargon unless explaining what a previous doctor told you).
- Answer the student's question accurately based ON THIS CASE DATA ONLY:
{request.case_text}
- Keep your answer short (1-3 sentences maximum).
- If the student asks about a symptom not mentioned in the case, say you don't think so or aren't sure."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.question}
            ],
            temperature=0.3,
            max_tokens=200
        )
        reply = response.choices[0].message.content.strip()
        return {"response": reply}

    except Exception as e:
        print(f"❌ [PATIENT API ERROR]: {type(e).__name__} -> {e}")
        return {"response": "I'm feeling a bit overwhelmed and can't answer right now."}

class InterjectionRequest(BaseModel):
    session_id: str
    interjection: str

# ─────────────────────────────────────────
# SESSION STORE
# Keeps track of active debate sessions
# ─────────────────────────────────────────

active_sessions = {}

# ─────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────

@app.get("/")
def health_check():
    return {"status": "Aletheia is running", "version": "1.0.0"}

# ─────────────────────────────────────────
# REST ENDPOINT — quick sync debate
# ─────────────────────────────────────────

@app.post("/debate")
async def run_debate_sync(submission: CaseSubmission):
    from graph.debate_graph import run_debate

    session_id = str(uuid.uuid4())

    # Retrieve matching past precedent from ChromaDB
    precedents = get_similar_cases(submission.case_text, n_results=1)
    augmented_case_text = f"{submission.case_text}\n\n[RELEVANT PAST CASE PRECEDENT FROM CHROMADB]:\n{precedents}"

    result = run_debate(
        case_text=augmented_case_text,
        user_diagnosis=submission.user_diagnosis,
        severity_flag=submission.severity_flag,
        mode=submission.mode,
        manual_specialists=submission.manual_specialists
    )

    return {
        "session_id": session_id,
        "status": result["status"],
        "triage": result["triage_result"],
        "selected_specialists": result["selected_specialists"],
        "debate_log": result["debate_log"],
        "final_verdict": result["final_verdict"],
        "comparison": result["comparison_result"]["response"] if result["comparison_result"] else None
    }

# ─────────────────────────────────────────
# WEBSOCKET ENDPOINT — live streaming debate
# ─────────────────────────────────────────

@app.websocket("/debate/stream")
async def debate_stream(websocket: WebSocket):
    await websocket.accept()

    session_id = str(uuid.uuid4())

    try:
        # Receive case submission from frontend
        data = await websocket.receive_text()
        submission_data = json.loads(data)

        raw_case_text = submission_data.get("case_text", "")
        user_diagnosis = submission_data.get("user_diagnosis", "")
        severity_flag = submission_data.get("severity_flag")
        mode = submission_data.get("mode", "doctor")
        manual_specialists = submission_data.get("manual_specialists")
        interjection_log = []

        # Store session
        active_sessions[session_id] = {
            "status": "running",
            "interjections": []
        }

        # Send session ID back to frontend immediately
        await websocket.send_text(json.dumps({
            "type": "session_start",
            "session_id": session_id
        }))

        # ── CHROMADB RAG LOOKUP ──
        await websocket.send_text(json.dumps({
            "type": "status",
            "message": "Querying ChromaDB vector database for clinical precedents..."
        }))

        precedents = get_similar_cases(raw_case_text, n_results=1)
        case_text = f"{raw_case_text}\n\n[HISTORICAL PRECEDENT RETRIEVED FROM CHROMADB]:\n{precedents}"

        # ── STEP 1: TRIAGE ──
        await websocket.send_text(json.dumps({
            "type": "status",
            "message": "Running triage assessment..."
        }))

        from agents.triage import run_triage, reconcile_with_user_flag
        triage_result = run_triage(case_text)
        triage_result = reconcile_with_user_flag(triage_result, severity_flag)

        await websocket.send_text(json.dumps({
            "type": "triage",
            "severity": triage_result["severity"],
            "reason": triage_result["reason"]
        }))

        # ── STEP 2: SELECT SPECIALISTS ──
        await websocket.send_text(json.dumps({
            "type": "status",
            "message": "Selecting specialist panel..."
        }))

        from agents.selector import run_selector
        selector_result = run_selector(case_text, manual_specialists)
        selected_specialists = selector_result["selected"]

        await websocket.send_text(json.dumps({
            "type": "specialists_selected",
            "specialists": selected_specialists,
            "mode": selector_result["mode"]
        }))

        # ── STEP 3: DEBATE ROUNDS ──
        debate_log = []

        from agents.specialist_runner import run_specialist
        from agents.skeptic import run_skeptic

        EXCHANGES_PER_ROUND = 1
        CALL_DELAY_SECONDS = 2.5

        for round_num in range(1, 3):  # 2 rounds
            await websocket.send_text(json.dumps({
                "type": "round_start",
                "round": round_num
            }))

            for exchange_num in range(1, EXCHANGES_PER_ROUND + 1):
                for specialist_name in selected_specialists:
                    await websocket.send_text(json.dumps({
                        "type": "agent_thinking",
                        "agent": specialist_name,
                        "round": round_num
                    }))

                    # Check for any pending interjections
                    if active_sessions[session_id]["interjections"]:
                        interjection = active_sessions[session_id]["interjections"].pop(0)
                        interjection_log.append(interjection)

                        from agents.chair import run_chair_interjection
                        chair_response = run_chair_interjection(
                            case_text, debate_log, interjection
                        )
                        debate_log.append(chair_response)

                        await websocket.send_text(json.dumps({
                            "type": "interjection_acknowledged",
                            "agent": "chair",
                            "response": chair_response["response"]
                        }))

                    response = run_specialist(
                        specialist_name=specialist_name,
                        case_text=case_text,
                        debate_log=debate_log,
                        round_number=round_num
                    )
                    debate_log.append(response)

                    # Stream this agent's response to frontend
                    await websocket.send_text(json.dumps({
                        "type": "agent_response",
                        "agent": specialist_name,
                        "round": round_num,
                        "exchange": exchange_num,
                        "response": response["response"],
                        "confidence": response["confidence"],
                        "api_used": response["api_used"]
                    }))

                    await asyncio.sleep(CALL_DELAY_SECONDS)

                    # Skeptic checks THIS individual opinion
                    skeptic_response = run_skeptic(case_text, debate_log)
                    debate_log.append(skeptic_response)
                    print(f"[SKEPTIC - HIDDEN] Round {round_num}, checking {specialist_name}: {skeptic_response['response']}")

                    await asyncio.sleep(CALL_DELAY_SECONDS)

            await websocket.send_text(json.dumps({
                "type": "round_end",
                "round": round_num
            }))

        # ── STEP 4: CHAIR VERDICT ──
        await websocket.send_text(json.dumps({
            "type": "agent_thinking",
            "agent": "chair",
            "round": "final"
        }))

        from agents.chair import run_chair_verdict
        chair_result = run_chair_verdict(case_text, debate_log)
        debate_log.append(chair_result)

        await websocket.send_text(json.dumps({
            "type": "verdict",
            "response": chair_result["response"]
        }))

        await asyncio.sleep(0.5)

        # ── STEP 5: COMPARISON ──
        await websocket.send_text(json.dumps({
            "type": "status",
            "message": "Unsealing your diagnosis and running comparison..."
        }))

        from agents.comparison import run_comparison
        comparison_result = run_comparison(
            user_diagnosis=user_diagnosis,
            panel_verdict=chair_result["response"],
            debate_log=debate_log,
            mode=mode,
            interjection_log=interjection_log
        )

        await websocket.send_text(json.dumps({
            "type": "comparison",
            "response": comparison_result["response"]
        }))

        await asyncio.sleep(0.5)

        # ── DONE ──
        await websocket.send_text(json.dumps({
            "type": "debate_complete",
            "session_id": session_id,
            "total_agents": len(debate_log)
        }))

        active_sessions[session_id]["status"] = "complete"

    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected")
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": str(e)
        }))
    finally:
        if session_id in active_sessions:
            del active_sessions[session_id]


# ─────────────────────────────────────────
# INTERJECTION ENDPOINT
# ─────────────────────────────────────────

@app.post("/debate/interject")
async def interject(request: InterjectionRequest):
    session_id = request.session_id
    if session_id not in active_sessions:
        return {"error": "Session not found or already complete"}

    active_sessions[session_id]["interjections"].append(request.interjection)
    return {"status": "interjection queued", "session_id": session_id}


# ─────────────────────────────────────────
# SPECIALIST LIST ENDPOINT
# ─────────────────────────────────────────

@app.get("/specialists")
def get_specialists():
    from agents.specialists import SPECIALIST_DESCRIPTIONS
    return {
        "specialists": [
            {"name": k, "description": v}
            for k, v in SPECIALIST_DESCRIPTIONS.items()
        ]
    }