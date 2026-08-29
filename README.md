# 🧠 SynthMind — Adaptive Research & Decision Intelligence Partner

> **"Don't just search. Think together."**

**Track: The Collaborative Partner** | **All Things Agentic Hackathon 2026**

---

## 🎯 Problem

Every day, billions of people drown in information overload when making complex decisions — students researching papers, professionals evaluating vendors, homebuyers comparing properties, patients understanding treatments. Current AI tools are **passive** — they answer questions but don't actively guide your thinking, synthesize across multiple data sources, or adapt to how YOU think.

## 💡 Solution

SynthMind is a **Collaborative Partner agent** that transforms chaotic research into structured decisions through adaptive co-thinking. It doesn't wait for you to ask the right questions — it **LEADS** you through a structured research methodology, actively **synthesizes** your data into decision frameworks, and **adapts** to your unique thinking style.

### What Makes SynthMind Different

| Feature | Traditional AI | SynthMind |
|---|---|---|
| Interaction | Waits for questions | **Leads with questions** |
| Data Handling | Reads and summarizes | **Synthesizes into new structures** |
| Output | Text responses | **Decision matrices, knowledge maps, SWOT analyses** |
| Adaptation | None | **Learns your thinking style** |
| Data Input | Text only | **PDFs, images, URLs, voice, camera** |

---

## 🏗️ Architecture

![Architecture Diagram](architecture-diagram.png)

### Hexagonal Architecture (Clean Separation)

```
synthmind/
├── backend/
│   ├── core/              # 🧠 Domain (ZERO external deps)
│   │   ├── agents/        # 5 ADK-powered agents
│   │   ├── models/        # Pure Python domain models
│   │   ├── events/        # Event bus for decoupled comms
│   │   └── interfaces/    # Port abstractions
│   ├── adapters/          # 🔌 External service implementations
│   ├── api/               # 🌐 FastAPI REST layer
│   ├── observability/     # 📊 Structured logging + tracing
│   └── config/            # ⚙️ Environment-based config
└── frontend/              # 🎨 Next.js premium UI
```

### Multi-Agent System (Google ADK)

| Agent | Role | Specialization |
|---|---|---|
| 🎯 **Orchestrator** | Root coordinator | State machine, routing, workflow |
| 🔍 **Clarifier** | Socratic questioner | Understands goals, constraints, preferences |
| 📄 **Ingester** | Data processor | PDFs, images, URLs, text → structured data |
| ⚡ **Synthesizer** | Intelligence creator | Decision matrices, comparisons, SWOT, insights |
| 🧬 **Adapter** | Style learner | Tracks thinking style, adjusts experience |

---

## 🛠️ Tech Stack

| Requirement | Technology | Cost |
|---|---|---|
| **AI Model** | Gemini 3.7 Flash via Gemini API | Free (AI Studio) |
| **Agent Framework** | Google ADK | Free (Open Source) |
| **Cloud Service** | Firebase Firestore | Free (Spark Plan) |
| **Backend** | Python 3.13 + FastAPI | Free |
| **Frontend** | Next.js 14 + TypeScript | Free |
| **Deployment** | Firebase Hosting | Free |

---

## 🚀 Setup Instructions

### Prerequisites
- Python 3.10+
- Node.js 18+
- Gemini API key from [aistudio.google.com](https://aistudio.google.com)

### Backend Setup

```bash
cd synthmind/backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Run the server
python main.py
```

The backend starts at `http://localhost:8000`

### Frontend Setup

```bash
cd synthmind/frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The frontend starts at `http://localhost:3000`

---

## 📊 Features

### 5 Input Modalities
- ⌨️ **Text** — Type questions and paste content
- 🎤 **Voice** — Speak naturally (Web Speech API)
- 📁 **Files** — Drag-and-drop PDFs, images, CSVs
- 🔗 **URLs** — Paste links for auto-analysis
- 📷 **Camera** — Snap photos of documents (mobile)

### 7 Synthesis Output Types
- 📊 **Decision Matrix** — Weighted scoring grid
- 📋 **Comparison Table** — Side-by-side with highlights
- ⚖️ **Pros/Cons** — With confidence scores
- 🔄 **SWOT Analysis** — Strategic quadrant view
- 💡 **Key Insights** — Ranked actionable takeaways
- 🗺️ **Knowledge Map** — Connected concept graph
- 📅 **Timeline** — Chronological milestones

### Adaptive Experience
- 🧬 **Thinking Style Detection** — Learns across 6 dimensions
- 🔄 **Feedback Loop** — Continuous improvement from user input
- 💾 **Persistent Memory** — Cross-session learning via Firestore

---

## 📹 Demo Video

[Watch on YouTube](YOUR_YOUTUBE_LINK_HERE)

---

## 👤 Team

Built for the **All Things Agentic Hackathon 2026** by a solo developer.

## 📝 License

MIT License — Built for the All Things Agentic Hackathon 2026.

#AllThingsAgenticHackathon
