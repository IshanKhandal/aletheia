import asyncio
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from agents.triage import run_triage, reconcile_with_user_flag
from agents.selector import run_selector
from agents.specialist_runner import run_specialist
from agents.skeptic import run_skeptic
from agents.chair import run_chair_verdict, run_chair_interjection
from agents.comparison import run_comparison

# ─────────────────────────────────────────
# 1. STATE — everything the graph carries
# ─────────────────────────────────────────
class DebateState(TypedDict):
    # Inputs
    case_text: str
    user_diagnosis: str
    severity_flag: Optional[str]
    mode: str
    manual_specialists: Optional[List[str]]

    # Computed during debate
    triage_result: Optional[dict]
    selected_specialists: Optional[List[str]]
    debate_log: List[dict]
    current_round: int
    interjection_log: List[str]
    final_verdict: Optional[str]
    comparison_result: Optional[dict]
    status: str  # "running" | "complete" | "error"


# ─────────────────────────────────────────
# 2. NODE FUNCTIONS — one per step
# ─────────────────────────────────────────

def node_triage(state: DebateState) -> DebateState:
    """Runs Triage Agent — fast blind severity check."""
    print("\n[ALETHEIA] Running triage...")
    result = run_triage(state["case_text"])
    result = reconcile_with_user_flag(result, state.get("severity_flag"))
    print(f"[TRIAGE] {result['severity']} — {result['reason']}")
    return {**state, "triage_result": result}


def node_select_specialists(state: DebateState) -> DebateState:
    """Selector Agent picks 4 specialists."""
    print("\n[ALETHEIA] Selecting specialists...")
    result = run_selector(
        state["case_text"],
        state.get("manual_specialists")
    )
    print(f"[SELECTOR] Selected: {result['selected']} (mode: {result['mode']})")
    return {**state, "selected_specialists": result["selected"]}


def node_debate_round(state: DebateState) -> DebateState:
    """
    Runs one full debate round:
    All 4 selected specialists respond, then Skeptic challenges.
    """
    round_num = state["current_round"]
    print(f"\n[ALETHEIA] Starting debate round {round_num}...")

    debate_log = list(state["debate_log"])

    # Run all 4 specialists
    for specialist_name in state["selected_specialists"]:
        print(f"[DEBATE] {specialist_name.upper()} responding...")

        # Build context: case + what's been said so far
        context = state["case_text"]
        if debate_log:
            prior = "\n\n".join([
                f"{r['agent_name'].upper()} (Round {r['round_number']}):\n{r['response']}"
                for r in debate_log
            ])
            context = f"{state['case_text']}\n\nDEBATE SO FAR:\n{prior}"

        response = run_specialist(specialist_name, context, round_num)
        debate_log.append(response)
        print(f"[DEBATE] {specialist_name.upper()} done. Confidence: {response['confidence']}")

    # Run Skeptic after all specialists
    print(f"[DEBATE] SKEPTIC reviewing round {round_num}...")
    skeptic_response = run_skeptic(state["case_text"], debate_log)
    debate_log.append(skeptic_response)
    print(f"[DEBATE] SKEPTIC done.")

    return {
        **state,
        "debate_log": debate_log,
        "current_round": round_num + 1
    }


def node_chair_verdict(state: DebateState) -> DebateState:
    """Chair synthesizes full debate and delivers final verdict."""
    print("\n[ALETHEIA] Chair delivering final verdict...")
    result = run_chair_verdict(state["case_text"], state["debate_log"])
    print(f"[CHAIR] Verdict delivered.")
    return {**state, "final_verdict": result["response"]}


def node_comparison(state: DebateState) -> DebateState:
    """Unseals user diagnosis and runs comparison."""
    print("\n[ALETHEIA] Running comparison...")
    result = run_comparison(
        user_diagnosis=state["user_diagnosis"],
        panel_verdict=state["final_verdict"],
        debate_log=state["debate_log"],
        mode=state["mode"],
        interjection_log=state.get("interjection_log", [])
    )
    print(f"[COMPARISON] Done.")
    return {
        **state,
        "comparison_result": result,
        "status": "complete"
    }


# ─────────────────────────────────────────
# 3. ROUTING — when to stop debating
# ─────────────────────────────────────────

def should_continue_debate(state: DebateState) -> str:
    """
    Hard cap at 2 rounds.
    After 2 rounds → go to Chair verdict.
    """
    if state["current_round"] > 2:
        return "chair"
    return "debate"


# ─────────────────────────────────────────
# 4. BUILD THE GRAPH
# ─────────────────────────────────────────

def build_debate_graph():
    graph = StateGraph(DebateState)

    # Add all nodes
    graph.add_node("triage", node_triage)
    graph.add_node("select", node_select_specialists)
    graph.add_node("debate", node_debate_round)
    graph.add_node("chair", node_chair_verdict)
    graph.add_node("comparison", node_comparison)

    # Define the flow
    graph.set_entry_point("triage")
    graph.add_edge("triage", "select")
    graph.add_edge("select", "debate")

    # Conditional: keep debating or go to chair
    graph.add_conditional_edges(
        "debate",
        should_continue_debate,
        {
            "debate": "debate",
            "chair": "chair"
        }
    )

    graph.add_edge("chair", "comparison")
    graph.add_edge("comparison", END)

    return graph.compile()


# ─────────────────────────────────────────
# 5. MAIN RUN FUNCTION
# ─────────────────────────────────────────

def run_debate(
    case_text: str,
    user_diagnosis: str,
    severity_flag: str = None,
    mode: str = "doctor",
    manual_specialists: list = None,
    interjection_log: list = None
) -> dict:
    """
    Main entry point to run a full Aletheia debate.
    Returns the complete final state.
    """
    graph = build_debate_graph()

    initial_state = DebateState(
        case_text=case_text,
        user_diagnosis=user_diagnosis,
        severity_flag=severity_flag,
        mode=mode,
        manual_specialists=manual_specialists,
        triage_result=None,
        selected_specialists=None,
        debate_log=[],
        current_round=1,
        interjection_log=interjection_log or [],
        final_verdict=None,
        comparison_result=None,
        status="running"
    )

    final_state = graph.invoke(initial_state)
    return final_state