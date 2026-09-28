const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function formatErrorDetail(detail) {
  if (!detail) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item?.msg) {
          const loc = Array.isArray(item.loc) ? item.loc.join(".") : "";
          return loc ? `${loc}: ${item.msg}` : item.msg;
        }
        return JSON.stringify(item);
      })
      .join("; ");
  }
  if (typeof detail === "object" && detail.msg) return detail.msg;
  return String(detail);
}

async function request(endpoint, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("Server returned an invalid response.");
  }

  if (!response.ok) {
    throw new Error(
      formatErrorDetail(data?.detail) || data?.message || "Something went wrong. Please try again."
    );
  }
  return data;
}

export async function learnTopic(topic, mode = "simple", userEmail) {
  return request("/api/learn", {
    method: "POST",
    body: JSON.stringify({
      topic: topic.trim(),
      mode,
      user_email: userEmail || "guest@learnwise.com",
    }),
  });
}

export async function submitQuiz(sessionId, answers, userEmail) {
  if (!sessionId) throw new Error("Missing session_id. Generate a lesson first.");
  if (!Array.isArray(answers) || answers.length === 0) throw new Error("Answers are required.");
  return request("/api/quiz/submit", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      answers,
      user_email: userEmail || "guest@learnwise.com",
    }),
  });
}

export async function getHistory(email, limit = 20) {
  return request(
    `/api/history?email=${encodeURIComponent(email || "guest@learnwise.com")}&limit=${limit}`,
    { method: "GET" }
  );
}

export async function getProgress(email) {
  return request(
    `/api/progress?email=${encodeURIComponent(email || "guest@learnwise.com")}`,
    { method: "GET" }
  );
}

export async function getMastery(email) {
  return request(
    `/api/mastery?email=${encodeURIComponent(email || "guest@learnwise.com")}`,
    { method: "GET" }
  );
}

export async function askTutor({ topic, action, concept, context, previous_strategies, userEmail }) {
  return request("/api/tutor", {
    method: "POST",
    body: JSON.stringify({
      topic,
      action,
      concept: concept || null,
      context: context || null,
      previous_strategies: previous_strategies || [],
      user_email: userEmail || "guest@learnwise.com",
    }),
  });
}

export async function startRevision(userEmail, topic) {
  return request("/api/revision", {
    method: "POST",
    body: JSON.stringify({
      user_email: userEmail || "guest@learnwise.com",
      topic: topic || null,
    }),
  });
}

export async function startAdaptivePractice(topic, difficulty, userEmail) {
  return request("/api/practice/adaptive", {
    method: "POST",
    body: JSON.stringify({
      topic: topic.trim(),
      difficulty: difficulty || "medium",
      user_email: userEmail || "guest@learnwise.com",
    }),
  });
}

export async function generateFlashcards(topic, concepts, userEmail) {
  return request("/api/flashcards", {
    method: "POST",
    body: JSON.stringify({
      topic: topic.trim(),
      concepts: concepts || [],
      user_email: userEmail || "guest@learnwise.com",
    }),
  });
}

export async function generateLearningPath(topic, userEmail) {
  return request("/api/learning-path", {
    method: "POST",
    body: JSON.stringify({
      topic: topic.trim(),
      user_email: userEmail || "guest@learnwise.com",
    }),
  });
}

export async function generateStudyPlan(payload) {
  return request("/api/study-plan", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function checkHealth() {
  return request("/api/health", { method: "GET" });
}

export async function uploadDocument(file, userEmail) {
  const body = new FormData();
  body.append("file", file);
  body.append("user_email", userEmail || "guest@learnwise.com");
  return request("/api/documents", { method: "POST", body });
}

export async function listDocuments(email) {
  return request(`/api/documents?email=${encodeURIComponent(email || "guest@learnwise.com")}`);
}

export async function deleteDocument(id, email) {
  return request(
    `/api/documents/${encodeURIComponent(id)}?email=${encodeURIComponent(email)}`,
    { method: "DELETE" }
  );
}

export async function askRag(question, userEmail, documentIds) {
  return request("/api/rag/ask", {
    method: "POST",
    body: JSON.stringify({
      question,
      user_email: userEmail || "guest@learnwise.com",
      document_ids: documentIds || null,
    }),
  });
}

export async function runAgent(message, userEmail, topic) {
  return request("/api/agent", {
    method: "POST",
    body: JSON.stringify({
      message,
      user_email: userEmail || "guest@learnwise.com",
      topic: topic || null,
    }),
  });
}

export async function getRecommendation(email, examDate, goal) {
  const params = new URLSearchParams({ email: email || "guest@learnwise.com" });
  if (examDate) params.set("exam_date", examDate);
  if (goal) params.set("goal", goal);
  return request(`/api/recommend?${params.toString()}`);
}

export async function getKnowledgeGraph() {
  return request("/api/knowledge-graph");
}

export async function getMasteryPredictions(email) {
  return request(`/api/mastery/predict?email=${encodeURIComponent(email || "guest@learnwise.com")}`);
}

export async function getObservability(email) {
  return request(`/api/observability?email=${encodeURIComponent(email || "guest@learnwise.com")}`);
}
