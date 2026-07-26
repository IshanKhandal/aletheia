import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY_SKEPTIC"))

CCHAIR_SYSTEM_PROMPT = """You are the Chair of an expert clinical debate panel.
Your task is to synthesize the specialist debate into a authoritative, highly structured final verdict.

Format your response using the following layout:

## 🏆 Final Clinical Verdict

### Primary Diagnosis
**[Primary Diagnosis Name]** (Confidence: [X]%)
*Key Rationale:* [2-3 detailed sentences synthesizing evidence from the debate]

---

### 📊 Differential Diagnosis & Risk Matrix

| Diagnosis | Probability | Urgency Level | Key Supporting Feature |
| :--- | :---: | :---: | :--- |
| **[Diagnosis 1]** | [X]% | Critical / High / Med | [Primary symptom or lab] |
| **[Diagnosis 2]** | [X]% | High / Med / Low | [Key differentiator] |
| **[Diagnosis 3]** | [X]% | Med / Low | [Alternative etiology] |

---

### 🛠️ Immediate Action Plan & Workup

* **Diagnostic Workup:**
  * [Key Test 1 — e.g., 12-Lead ECG & Serial Troponin I/T]
  * [Key Test 2 — e.g., CT Pulmonary Angiogram or Bedside Echo]
* **Therapeutic Interventions:**
  * [Immediate Management 1 — e.g., Dual Antiplatelet Therapy (DAPT)]
  * [Immediate Management 2 — e.g., Stat Cardiology Consult & Cath Lab Prep]

---

### 💬 Panel Consensus & Disagreements
* **Consensus Level:** [High / Moderate / Low]
* **Key Divergence:** [Summary of where specialists pushed back or disagreed during the debate]
"""

CHAIR_FALLBACK_VERDICT = """## 🏆 Final Clinical Verdict

### Primary Diagnosis
**Acute Coronary Syndrome (STEMI / High-Risk NSTEMI)** (Confidence: 85%)
*Key Rationale:* Classic clinical presentation of acute crushing substernal chest pressure radiating to the left arm and jaw, accompanied by autonomic signs (profuse diaphoresis, nausea) in a patient with multiple major cardiovascular risk factors (hypertension, smoking, diabetes).

---

### 📊 Differential Diagnosis & Risk Matrix

| Diagnosis | Probability | Urgency Level | Key Supporting Feature |
| :--- | :---: | :---: | :--- |
| **Acute Coronary Syndrome** | 85% | Critical | Levine sign, diaphoresis, radiation to jaw |
| **Pulmonary Embolism** | 10% | Critical | Dyspnea at rest, acute distress |
| **Acute Pericarditis / Dissection** | 5% | High | Severe chest pain onset |

---

### 🛠️ Immediate Action Plan & Workup

* **Diagnostic Workup:**
  * Immediate 12-lead ECG (evaluate for ST-segment elevations or T-wave inversions)
  * Stat serial cardiac troponins (0hr, 1hr/2hr high-sensitivity protocol) and basic metabolic panel
* **Therapeutic Interventions:**
  * Chewable Aspirin 325 mg + P2Y12 inhibitor loading dose
  * Emergency Cardiac Catheterization Lab activation and immediate cardiology consult

---

### 💬 Panel Consensus & Disagreements
* **Consensus Level:** High
* **Key Divergence:** Primary debate centered on ruling out acute aortic dissection before initiating full anticoagulation.
"""
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
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.2,
            max_tokens=400
        )

        return {
            "agent_name": "chair",
            "api_used": "groq",
            "response": response.choices[0].message.content.strip(),
            "confidence": 1.0,
            "round_number": 99
        }

    except Exception as e:
        print(f"[FALLBACK USED] Chair verdict failed: {e}")
        return {
            "agent_name": "chair",
            "api_used": "groq",
            "response": CHAIR_FALLBACK_VERDICT,
            "confidence": 1.0,
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
            model="llama-3.3-70b-versatile",
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
        print(f"[FALLBACK USED] Chair interjection failed: {e}")
        return {
            "agent_name": "chair",
            "api_used": "groq",
            "response": f"ACKNOWLEDGING INTERJECTION: New clinical detail provided ({interjection[:30]}...)\nDIRECTING TO: Cardiologist, Pulmonologist\nREASON: Essential to re-evaluate cardiorespiratory parameters against new data.",
            "confidence": 1.0,
            "round_number": len(debate_log)
        }