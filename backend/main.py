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
# For testing without WebSockets
# ─────────────────────────────────────────

@app.post("/debate")
async def run_debate_sync(submission: CaseSubmission):
    """
    Runs a full debate synchronously.
    Returns complete result when done.
    Use /debate/stream for live streaming.
    """
    from graph.debate_graph import run_debate

    session_id = str(uuid.uuid4())

    result = run_debate(
        case_text=submission.case_text,
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
# This is the main endpoint for the frontend
# ─────────────────────────────────────────

@app.websocket("/debate/stream")
async def debate_stream(websocket: WebSocket):
    """
    WebSocket endpoint for live debate streaming.
    Frontend connects here to watch agents debate in real time.
    
    Message flow:
    1. Frontend sends case submission as JSON
    2. Backend streams each agent response as it's generated
    3. Frontend displays agents typing one by one
    """
    await websocket.accept()

    try:
        # Receive case submission from frontend
        data = await websocket.receive_text()
        submission_data = json.loads(data)

        session_id = str(uuid.uuid4())
        case_text = submission_data.get("case_text", "")
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

        for round_num in range(1, 5):  # 4 rounds max
            await websocket.send_text(json.dumps({
                "type": "round_start",
                "round": round_num
            }))

            # Each specialist responds
            for specialist_name in selected_specialists:
                await websocket.send_text(json.dumps({
                    "type": "agent_thinking",
                    "agent": specialist_name,
                    "round": round_num
                }))

                # Build context with debate so far
                context = case_text
                if debate_log:
                    prior = "\n\n".join([
                        f"{r['agent_name'].upper()} (Round {r['round_number']}):\n{r['response']}"
                        for r in debate_log
                    ])
                    context = f"{case_text}\n\nDEBATE SO FAR:\n{prior}"

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

                from agents.specialist_runner import run_specialist
                response = run_specialist(specialist_name, context, round_num)
                debate_log.append(response)

                # Stream this agent's response to frontend
                await websocket.send_text(json.dumps({
                    "type": "agent_response",
                    "agent": specialist_name,
                    "round": round_num,
                    "response": response["response"],
                    "confidence": response["confidence"],
                    "api_used": response["api_used"]
                }))

            # Skeptic reviews the round — runs in background, not shown to frontend
            from agents.skeptic import run_skeptic
            skeptic_response = run_skeptic(case_text, debate_log)
            debate_log.append(skeptic_response)
            print(f"[SKEPTIC - HIDDEN] Round {round_num}: {skeptic_response['response']}")

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
# User sends this while debate is running
# ─────────────────────────────────────────

@app.post("/debate/interject")
async def interject(request: InterjectionRequest):
    """
    User injects new information mid-debate.
    The Chair will route it to relevant specialists.
    """
    session_id = request.session_id
    if session_id not in active_sessions:
        return {"error": "Session not found or already complete"}

    active_sessions[session_id]["interjections"].append(request.interjection)
    return {"status": "interjection queued", "session_id": session_id}


# ─────────────────────────────────────────
# SPECIALIST LIST ENDPOINT
# Frontend uses this to show manual selection
# ─────────────────────────────────────────

@app.get("/specialists")
def get_specialists():
    """Returns the full roster of available specialists."""
    from agents.specialists import SPECIALIST_DESCRIPTIONS
    return {
        "specialists": [
            {"name": k, "description": v}
            for k, v in SPECIALIST_DESCRIPTIONS.items()
        ]
    }