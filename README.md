# LearnWise AI 🧠
### Adaptive Learning & AI-Powered Study Platform

LearnWise AI is an AI-powered learning platform designed to help students understand concepts, practice questions, identify weak areas, and organize their learning.

Unlike a basic chatbot, LearnWise combines AI-generated lessons, quizzes, learning progress, document-based question answering, and adaptive study suggestions in one application.

- **Live Demo:** https://learn-wise-ai-ruddy.vercel.app
- **GitHub Repository:** https://github.com/PankhaniyaShruti/LearnWise-AI

---

## ✨ Features

- **AI-Powered Lessons:** Generate learning content in different modes, including simple, detailed, study, story, exam, and practical.
- **Diagnostic Quizzes:** Attempt quizzes, receive scores, and identify weak concepts.
- **Adaptive Practice:** Practice topics at different difficulty levels and receive revision suggestions.
- **Learning Progress:** View learning history, mastery information, and recommendations.
- **Document-Based Q&A:** Upload supported PDF or TXT notes and ask questions using retrieved content.
- **Knowledge Graph:** Explore predefined concept relationships and learning prerequisites.
- **Agent Orchestration:** Route supported requests through specialized learning components.
- **ML Mastery Estimation:** Use Logistic Regression experimentation alongside rule-based mastery logic.
- **LLMOps Monitoring:** Record selected model usage, prompt versions, latency, token information, and request status.

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| Frontend | React 19, Vite |
| Backend | Python, FastAPI |
| Data Validation | Pydantic |
| Generative AI | Groq, optional xAI provider |
| Machine Learning | scikit-learn, Logistic Regression |
| Document Processing | PyPDF |
| Retrieval | TF-IDF, Cosine Similarity |
| Database | SQLite |
| Tools | Git, GitHub, VS Code |

## 🏗️ Architecture

```text
             React + Vite
                  |
                  v
             FastAPI Backend
                  |
        +---------+----------+
        |         |          |
        v         v          v
    LLM Gateway  Learning   Document
                 Workflows  Retrieval
        |         |          |
        v         v          v
    AI Provider  Quiz &    TF-IDF
                 Mastery   Search
        |
        v
     Groq / xAI

          SQLite Storage
                |
       Progress & Events
```

Architecture documentation: [docs/ARCHITECTURE.md](https://github.com/PankhaniyaShruti/LearnWise-AI/blob/main/docs/ARCHITECTURE.md)

## 📚 Learning Workflow

```text
Select Topic
     ↓
Choose Learning Mode
     ↓
Generate Lesson
     ↓
Review Key Concepts
     ↓
Attempt Diagnostic Quiz
     ↓
View Score & Weak Areas
     ↓
Track Learning Progress
     ↓
Receive Learning Suggestions
```

The current application opens directly to the learning interface without requiring a login screen for the demonstrated workflow.

## 📄 Document-Based Question Answering (RAG)

LearnWise includes a document question-answering workflow for supported PDF and TXT files.

### How it works

1. Upload a supported document.
2. Extract available text.
3. Split the text into chunks.
4. Retrieve relevant content using TF-IDF similarity.
5. Generate an answer based on retrieved context.
6. Display citations associated with retrieved document chunks.

**Technical note:** The current retrieval approach uses TF-IDF rather than a hosted vector database. Scanned PDFs without extractable text may not be supported.

## 🤖 Agent Orchestration

LearnWise includes an orchestration workflow that selects relevant learning components for supported requests.

For example, a study-planning request may involve:

1. Reviewing available mastery information.
2. Retrieving relevant uploaded notes.
3. Applying planning logic.
4. Using revision or tutoring functionality where appropriate.

This is a lightweight application-level orchestration approach rather than a claim of a fully autonomous multi-agent system.

## 🧪 Machine Learning

The mastery prediction component uses Logistic Regression trained on synthetic bootstrap data.

Rule-based mastery logic is also used in the learning workflow.

The model is intended for experimentation and demonstration. Synthetic training and evaluation results should not be interpreted as validated real-world student performance.

## ⚙️ Run Locally

### Requirements

- Python 3.10+
- Node.js
- npm
- An API key for the configured LLM provider when using live AI generation

### 1. Clone the repository

```bash
git clone https://github.com/PankhaniyaShruti/LearnWise-AI.git
cd LearnWise-AI
```

### 2. Backend Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.\.venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r backend\requirements.txt
```

Create a `.env` file using `.env.example` and configure the required provider credentials.

Start the backend:

```powershell
python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

### 3. Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the application at http://localhost:5173.

## 🔑 Environment Configuration

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Groq API access |
| `XAI_API_KEY` | Optional xAI provider |
| `LLM_PROVIDER` | LLM provider selection |
| `GROQ_MODEL*` | Groq model configuration |
| `VITE_API_BASE_URL` | Optional API base URL |
| `DATABASE_PATH` | SQLite database location |

Keep API credentials in environment variables. Never commit secrets or your `.env` file.

## 🧪 Development Checks

Frontend build:

```bash
cd frontend
npm run build
```

Backend checks:

```bash
python -m compileall backend
pytest tests -q
```

Additional evaluation and model-training scripts are available in the repository.

## ⚠️ Limitations

- SQLite is used for demo storage; persistence depends on the hosting environment.
- The hosted demo may use temporary writable storage.
- The current direct-access workflow is not production-grade authentication.
- Document retrieval uses TF-IDF.
- The mastery classifier uses synthetic bootstrap data.
- AI functionality depends on provider availability, API credentials, and rate limits.
- Scanned image-only PDFs may not contain extractable text.

## 👩‍💻 About

**Shruti Pankhaniya**  
MCA Student | Artificial Intelligence & Machine Learning

[GitHub Profile](https://github.com/PankhaniyaShruti)

---

*Built as a hands-on project exploring Generative AI, adaptive learning, document retrieval, and machine learning.*
