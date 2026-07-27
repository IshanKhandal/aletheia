# 🩺 Aletheia — Multi-Agent AI Clinical Reasoning Panel

[![Vercel Deployment](https://img.shields.io/badge/Frontend-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://aletheia-bkxy.vercel.app)
[![Render Backend](https://img.shields.io/badge/Backend-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://aletheia-backend.onrender.com)
[![Python FastAPI](https://img.shields.io/badge/API-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![ChromaDB RAG](https://img.shields.io/badge/Vector_DB-ChromaDB-FF6F00?style=for-the-badge&logo=python&logoColor=white)](https://www.trychroma.com/)

> **Aletheia** *(Greek for "uncovering truth")* is an adversarial, multi-agent AI clinical reasoning board designed to mitigate cognitive diagnostic errors in emergency medicine. Rather than relying on a single AI model, Aletheia provisions a panel of specialized AI agents that debate, challenge, and cross-examine patient cases in real time before delivering an evidence-backed consensus.

---

## 🚀 Live Deployments

* **Frontend Web App:** [https://aletheia-bkxy.vercel.app](https://aletheia-bkxy.vercel.app)
* **Backend API Service:** [https://aletheia-backend.onrender.com](https://aletheia-backend.onrender.com)

---

## 🎯 What Aletheia Does

In fast-paced emergency settings, clinicians can fall victim to cognitive biases such as **anchoring bias** (sticking to an initial hunch) or **premature closure** (stopping the search for answers too early). Aletheia acts as an automated safety net by simulating a real-time hospital board debate.

* **Adversarial Panel Debates:** Brings together AI specialists (Cardiology, Pulmonology, Neurology, Intensivist) to cross-examine patient symptoms.
* **Grounding with ChromaDB (RAG):** Automatically queries an embedded vector database to retrieve historical clinical precedents, grounding the agents in past medical benchmark cases to avoid hallucinations.
* **The Skeptic Agent:** A dedicated adversarial agent whose sole job is to interrupt the panel, challenge confirmation bias, and highlight overlooked physical exam details (e.g., blood pressure differentials, subtle murmurs).
* **Blind Comparative Diagnosis:** The doctor's initial hypothesis stays sealed while the AI panel deliberates. Once the panel reaches a verdict, the doctor's diagnosis is unsealed and compared side-by-side to highlight potential blind spots.
* **Dual Operating Modes:**
  * **Doctor Mode:** Fast intake workflow designed for rapid decision support during ER shifts.
  * **Student Mode:** Interactive OSCE simulator where medical trainees interview an AI patient roleplaying from vignette data to practice taking structured histories.

---

## ⚡ Why ChromaDB? (Vector Search & RAG)

LLMs evaluating complex clinical vignettes often suffer from hallucination or anchoring on obvious symptoms. **ChromaDB serves as Aletheia's long-term vector memory.** Before any AI specialist begins debating, ChromaDB searches a vector database of benchmark medical cases to ground the panel in real clinical evidence.

### How ChromaDB Works in Aletheia:

1. **Semantic Vector Search:** When a case is submitted, ChromaDB converts the clinical narrative into high-dimensional vector embeddings. It matches clinical context rather than exact words (e.g., recognizing that *"tearing chest pain"* and *"sharp substrenal pressure with radiation"* share identical clinical significance).
2. **Context Augmentation (RAG):** The top-matching historical precedent retrieved from ChromaDB is automatically injected into the prompt payload before the debate begins.
3. **Bias Disruption:** The **Skeptic Agent** uses the retrieved precedent as hard evidence to challenge the panel—pointing out when a subtle detail (like a 30 mmHg blood pressure differential) matches a high-mortality precedent like Aortic Dissection.

---

## 🛠️ Tech Stack

### Frontend
* **Framework:** React / Vite
* **Styling:** Tailwind CSS
* **Data Visualization:** Chart.js
* **Hosting:** Vercel

### Backend
* **Core Framework:** Python / FastAPI
* **Vector Database (RAG):** ChromaDB
* **AI Models / Engines:** Groq (`llama-3.3-70b-versatile`), Google Gemini (`gemini-2.0-flash`)
* **Real-time Streaming:** WebSockets (`ws://`) & Async Uvicorn
* **Hosting:** Render

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
