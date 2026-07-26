# 🩺 Aletheia — Multi-Agent Clinical Reasoning Panel

**Aletheia** (ἀλήθεια — *the uncovering of truth*) is a real-time, multi-agent AI clinical reasoning platform. It simulates an adversarial multidisciplinary medical board where specialized AI agents debate complex patient cases, challenge each other's diagnostic hypotheses, and reach a consensus—all before unsealing the user's initial diagnosis for direct comparison.

---

## ✨ Key Features

- **Adversarial Specialist Debates:** Dynamically selects a tailored panel of specialists (e.g., Cardiologist, Pulmonologist, Neurologist, General Surgeon) to actively debate differential diagnoses.
- **Dedicated Skeptic & Chair:** A *Skeptic* agent continuously challenges assumptions to prevent premature agreement, while a *Chair* agent synthesizes the debate into a final structured verdict.
- **Sealed Diagnosis & Unsealed Comparison:** Users submit their baseline diagnostic hypothesis, which remains sealed until the board concludes its multi-round debate to ensure unbiased evaluation.
- **Dual Operating Modes:**
  - **Doctor Mode:** Fast-track case submission directly to triage and the specialist panel.
  - **Student Mode:** Interactive patient interview simulation allowing students to gather clinical history dynamically before presenting to the board.
- **Interactive Visual Analytics:** Opens a standalone analytics window featuring canvas particle animations, smooth probability progression line graphs across debate rounds, radar sensitivity charts, and clinical feature alignment matrix tables.
- **Live WebSocket Streaming:** Streams agent thought processes, multi-turn exchanges, and live mid-debate user interjections in real time.

---

## 🛠️ Tech Stack

- **Frontend:** React, TypeScript, Vite, Chart.js, React Markdown, CSS3 / Custom Dark Styling
- **Backend:** FastAPI, Python, WebSockets, Asyncio, Uvicorn
- **LLM Orchestration:** Groq API (`llama-3.3-70b-versatile`), Google Gemini API (`gemini-2.0-flash`)

---

## 📂 Project Structure

```text
aletheia/
├── backend/
│   ├── main.py              # FastAPI server & WebSocket endpoints
│   ├── requirements.txt     # Python dependencies
│   └── .env                 # API keys (Groq & Gemini)
└── aletheia-frontend/
    ├── public/
    │   └── analytics.html   # Standalone Visual Analytics & Particle Dashboard
    ├── src/
    │   ├── App.tsx          # Main console & debate stream UI
    │   └── components/
    │       └── Sphere.tsx   # Interactive 3D visual sphere component
    └── package.json
