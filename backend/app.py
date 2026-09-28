import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .agents.orchestrator import run_orchestrator
from .ai import generate_lesson
from .advanced_ai import (
    generate_adaptive_quiz,
    generate_flashcards,
    generate_learning_path,
    generate_revision_lesson,
    generate_study_plan,
    tutor_respond,
)
from .config import llm_available, supabase_configured
from .history import (
    clear_history,
    create_session,
    get_history,
    get_progress,
    get_quiz_history,
    get_session,
    save_quiz_result,
)
from .knowledge.graph import ensure_seeded, graph_payload, recommended_next_concepts
from .mastery import apply_quiz_to_mastery, get_achievements, get_mastery_profile
from .ml.predict import predict_profile
from .ml.train import load_metrics
from .models import (
    AdaptiveQuizRequest,
    AgentRequest,
    FlashcardsRequest,
    LearnRequest,
    LearningPathRequest,
    QuizSubmission,
    RagAskRequest,
    RevisionRequest,
    StudyPlanRequest,
    TutorRequest,
)
from .observability.events import list_usage_events
from .rag.pipeline import (
    ask_documents,
    delete_owned_document,
    get_owned_document,
    list_user_documents,
    process_upload,
)
from .recommend.engine import recommend_next_action

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        ensure_seeded()
    except Exception as error:
        logger.warning("Knowledge graph seed skipped: %s", error)
    yield


app = FastAPI(
    title="LearnWise AI — Adaptive Learning Intelligence & Agentic RAG Platform",
    version="4.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "LearnWise AI",
        "version": "4.0.0",
        "storage": "supabase" if supabase_configured() else "sqlite_demo",
        "llm_configured": llm_available(),
    }


@app.post("/api/learn")
def learn_endpoint(request: LearnRequest):
    logger.info("Learning request -> topic='%s', mode='%s', user='%s'", request.topic, request.mode, request.user_email)
    try:
        lesson = generate_lesson(topic=request.topic, mode=request.mode, user_email=request.user_email)
        session_id = create_session(
            user_email=request.user_email,
            topic=request.topic,
            mode=request.mode,
            lesson=lesson,
        )
        return {
            "session_id": session_id,
            "topic": request.topic,
            "mode": request.mode,
            "explanation": lesson["explanation"],
            "key_concepts": lesson["key_concepts"],
            "quiz": lesson["quiz"],
        }
    except RuntimeError as error:
        logger.error("AI generation error: %s", error)
        raise HTTPException(status_code=500, detail=f"Failed to generate the lesson: {str(error)}")
    except Exception as error:
        logger.error("Unexpected error: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected server error occurred.")


@app.post("/api/quiz/submit")
def submit_quiz(payload: QuizSubmission):
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Learning session not found.")

    session_owner = (session.get("user_email") or "").strip().lower()
    submitter = (payload.user_email or "").strip().lower()
    if not submitter or session_owner != submitter:
        raise HTTPException(status_code=403, detail="You are not allowed to submit a quiz for this session.")

    quiz = session.get("quiz") or []
    if not quiz:
        raise HTTPException(status_code=400, detail="This session has no quiz.")
    if not payload.answers:
        raise HTTPException(status_code=400, detail="Answers are required.")

    total = len(quiz)
    indices = [ans.question_index for ans in payload.answers]
    if len(indices) != total:
        raise HTTPException(status_code=400, detail=f"Expected exactly {total} answers, received {len(indices)}.")
    if len(set(indices)) != total:
        raise HTTPException(status_code=400, detail="Duplicate question_index values are not allowed.")
    if sorted(indices) != list(range(total)):
        raise HTTPException(status_code=400, detail=f"question_index values must be 0 through {total - 1}.")

    answer_map = {ans.question_index: ans.selected_answer for ans in payload.answers}
    for index, question in enumerate(quiz):
        selected = answer_map.get(index)
        if not selected or not str(selected).strip():
            raise HTTPException(status_code=400, detail=f"Answer for question {index} is empty.")
        options = question.get("options") or []
        if selected not in options:
            raise HTTPException(status_code=400, detail=f"selected_answer for question {index} is not a valid option.")

    score = 0
    weak_concepts: list[str] = []
    for index, question in enumerate(quiz):
        if answer_map[index] == question["correct_answer"]:
            score += 1
        else:
            concept = question.get("concept_tested")
            if concept and concept not in weak_concepts:
                weak_concepts.append(concept)

    percentage = round((score / total) * 100) if total else 0
    result = save_quiz_result(
        user_email=session_owner,
        session_id=payload.session_id,
        score=score,
        total=total,
        percentage=percentage,
        weak_concepts=weak_concepts,
    )
    mastery_updates = []
    try:
        mastery_updates = apply_quiz_to_mastery(
            user_email=session_owner,
            topic=session.get("topic") or "",
            quiz=quiz,
            answer_map=answer_map,
        )
    except Exception as error:
        logger.error("Mastery update failed (non-fatal): %s", error)

    if percentage == 100:
        performance = "Excellent! You mastered this topic."
    elif percentage >= 67:
        performance = "Good job! You understand most of it."
    elif percentage >= 34:
        performance = "You're getting there. Review the weak concepts."
    else:
        performance = "Review the lesson and try the quiz again."

    return {**result, "performance": performance, "mastery_updates": mastery_updates}


@app.get("/api/history")
def history_endpoint(
    email: str = Query(default="guest@learnwise.com"),
    limit: int = Query(default=20, ge=1, le=100),
):
    items = get_history(email, limit)
    return {"items": items, "total": len(items)}


@app.get("/api/quiz/history")
def quiz_history_endpoint(
    email: str = Query(default="guest@learnwise.com"),
    limit: int = Query(default=20, ge=1, le=100),
):
    items = get_quiz_history(email, limit)
    return {"items": items, "total": len(items)}


@app.get("/api/progress")
def progress_endpoint(email: str = Query(default="guest@learnwise.com")):
    base = get_progress(email)
    try:
        mastery = get_mastery_profile(email)
    except Exception as error:
        logger.error("Mastery profile failed: %s", error)
        mastery = {
            "overall_mastery": 0,
            "total_concepts": 0,
            "concepts": [],
            "weak_concepts": [],
            "strong_concepts": [],
            "critical_concepts": [],
            "improving_concepts": [],
            "due_for_review": [],
            "recommendations": [],
        }
    achievements = get_achievements(email, base, mastery)
    return {**base, "mastery": mastery, "achievements": achievements}


@app.get("/api/mastery")
def mastery_endpoint(email: str = Query(default="guest@learnwise.com")):
    try:
        return get_mastery_profile(email)
    except Exception as error:
        logger.error("Mastery error: %s", error)
        raise HTTPException(status_code=500, detail="Failed to load mastery profile.")


@app.post("/api/tutor")
def tutor_endpoint(payload: TutorRequest):
    try:
        return tutor_respond(
            topic=payload.topic,
            concept=payload.concept,
            action=payload.action,
            context=payload.context,
            previous_strategies=payload.previous_strategies,
            user_email=payload.user_email,
        )
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error))
    except Exception as error:
        logger.error("Tutor error: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Tutor request failed.")


@app.post("/api/revision")
def revision_endpoint(payload: RevisionRequest):
    try:
        profile = get_mastery_profile(payload.user_email)
        weak = profile.get("weak_concepts") or []
        if not weak and profile.get("concepts"):
            weak = sorted(profile["concepts"], key=lambda c: c.get("mastery_score", 0))[:3]
        if not weak:
            raise HTTPException(
                status_code=400,
                detail="No weak concepts yet. Complete a quiz first so we can personalize revision.",
            )
        topic = payload.topic or (weak[0].get("topic") if weak else "General review")
        concepts = [c["concept"] if isinstance(c, dict) else str(c) for c in weak[:5]]
        lesson = generate_revision_lesson(
            topic=topic or "General review",
            weak_concepts=concepts,
            user_email=payload.user_email,
        )
        session_id = create_session(
            user_email=payload.user_email,
            topic=f"Revision: {topic}",
            mode="study",
            lesson={
                "explanation": lesson["explanation"],
                "key_concepts": lesson.get("key_concepts") or concepts[:3],
                "quiz": lesson["quiz"],
            },
        )
        return {
            "session_id": session_id,
            "topic": f"Revision: {topic}",
            "mode": "study",
            "explanation": lesson["explanation"],
            "key_concepts": lesson.get("key_concepts") or concepts[:3],
            "quiz": lesson["quiz"],
            "focused_concepts": concepts,
        }
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Revision error: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create revision: {error}")


@app.post("/api/practice/adaptive")
def adaptive_practice(payload: AdaptiveQuizRequest):
    try:
        profile = get_mastery_profile(payload.user_email)
        weak = [c["concept"] for c in (profile.get("weak_concepts") or [])][:5]
        if not weak:
            weak = [c["concept"] for c in (profile.get("concepts") or [])[:3]]
        quiz = generate_adaptive_quiz(
            payload.topic, weak or [payload.topic], payload.difficulty, user_email=payload.user_email
        )
        session_id = create_session(
            user_email=payload.user_email,
            topic=payload.topic,
            mode=f"practice_{payload.difficulty}",
            lesson={
                "explanation": f"Adaptive practice focused on: {', '.join(weak) if weak else payload.topic}",
                "key_concepts": (weak + [payload.topic])[:3],
                "quiz": quiz,
            },
        )
        return {
            "session_id": session_id,
            "topic": payload.topic,
            "difficulty": payload.difficulty,
            "focus_concepts": weak,
            "quiz": quiz,
            "explanation": f"Adaptive practice focused on: {', '.join(weak) if weak else payload.topic}",
            "key_concepts": (weak + [payload.topic])[:3],
        }
    except Exception as error:
        logger.error("Adaptive practice error: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create adaptive practice: {error}")


@app.post("/api/flashcards")
def flashcards_endpoint(payload: FlashcardsRequest):
    try:
        cards = generate_flashcards(payload.topic, payload.concepts, user_email=payload.user_email)
        return {"topic": payload.topic, "cards": cards}
    except Exception as error:
        logger.error("Flashcards error: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate flashcards: {error}")


@app.post("/api/learning-path")
def learning_path_endpoint(payload: LearningPathRequest):
    try:
        path = generate_learning_path(payload.topic, user_email=payload.user_email)
        return path
    except Exception as error:
        logger.error("Learning path error: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate learning path: {error}")


@app.post("/api/study-plan")
def study_plan_endpoint(payload: StudyPlanRequest):
    try:
        topics = payload.topics or [payload.exam_name]
        plan = generate_study_plan(
            exam_name=payload.exam_name,
            exam_date=payload.exam_date,
            daily_minutes=payload.daily_minutes,
            level=payload.level,
            topics=topics,
            user_email=payload.user_email,
        )
        return plan
    except Exception as error:
        logger.error("Study plan error: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate study plan: {error}")


@app.delete("/api/history")
def clear_history_endpoint(email: str = Query(...)):
    clear_history(email)
    return {"status": "ok", "message": "History cleared."}


@app.post("/api/documents")
async def upload_document(
    file: UploadFile = File(...),
    user_email: str = Form(default="guest@learnwise.com"),
):
    data = await file.read()
    try:
        doc = process_upload(
            user_email=user_email,
            filename=file.filename or "upload.bin",
            data=data,
            content_type=file.content_type,
        )
        return doc
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.error("Upload error: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process document.")


@app.get("/api/documents")
def list_documents(email: str = Query(default="guest@learnwise.com")):
    return {"items": list_user_documents(email)}


@app.get("/api/documents/{document_id}")
def get_document(document_id: str, email: str = Query(default="guest@learnwise.com")):
    doc = get_owned_document(email, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: str, email: str = Query(...)):
    if not delete_owned_document(email, document_id):
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"status": "ok"}


@app.post("/api/rag/ask")
def rag_ask(payload: RagAskRequest):
    try:
        return ask_documents(
            user_email=payload.user_email,
            question=payload.question,
            document_ids=payload.document_ids,
        )
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        logger.error("RAG error: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to answer from documents.")


@app.post("/api/agent")
def agent_endpoint(payload: AgentRequest):
    try:
        return run_orchestrator(
            message=payload.message,
            user_email=payload.user_email,
            topic=payload.topic,
        )
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        logger.error("Agent error: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Orchestrator request failed.")


@app.get("/api/recommend")
def recommend_endpoint(
    email: str = Query(default="guest@learnwise.com"),
    exam_date: str | None = Query(default=None),
    goal: str | None = Query(default=None),
):
    mastery = get_mastery_profile(email)
    progress = get_progress(email)
    documents = list_user_documents(email)
    gaps = recommended_next_concepts([c["concept"] for c in (mastery.get("weak_concepts") or [])][:5])
    ml = predict_profile(email, mastery.get("concepts") or []) if mastery.get("concepts") else {"predictions": []}
    rec = recommend_next_action(
        mastery=mastery,
        progress=progress,
        documents=documents,
        exam_date=exam_date,
        learning_goal=goal,
        ml_predictions=ml.get("predictions") or [],
        prerequisite_gaps=gaps,
    )
    return {"recommendation": rec, "prerequisite_gaps": gaps[:8], "ml": ml}


@app.get("/api/knowledge-graph")
def knowledge_graph_endpoint():
    return graph_payload()


@app.get("/api/mastery/predict")
def mastery_predict(email: str = Query(default="guest@learnwise.com")):
    profile = get_mastery_profile(email)
    return predict_profile(email, profile.get("concepts") or [])


@app.get("/api/observability")
def observability_endpoint(
    email: str = Query(default="guest@learnwise.com"),
    limit: int = Query(default=40, ge=1, le=200),
):
    events = list_usage_events(email, limit=limit)
    return {
        "items": events,
        "total": len(events),
        "note": "Events are scoped to this learner. Prompts and document text are not stored.",
    }


@app.get("/api/eval/summary")
def eval_summary():
    return {
        "ml": load_metrics(),
        "rag": {
            "method": "TF-IDF cosine similarity over per-user chunks",
            "citation_policy": "Only retrieved chunk ids may be cited.",
        },
    }
