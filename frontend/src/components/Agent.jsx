import { useState } from "react";
import { runAgent } from "../api";

function Agent({ userEmail, topic }) {
  const [message, setMessage] = useState(
    "I have an ML exam in 10 days. I uploaded my notes. Make a study plan and teach me my weak topics."
  );
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    if (!message.trim()) return;
    try {
      setLoading(true);
      setError("");
      const data = await runAgent(message.trim(), userEmail, topic);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const tools = result?.tools_used || [];

  return (
    <section className="dashboard-section">
      <div className="card">
        <p className="section-number">AGENT</p>
        <h2>Orchestrated learning request</h2>
        <p className="quiz-subtitle">
          The planner routes to tutor, RAG, mastery, revision, assessment, or study-plan tools — not all of them every time.
        </p>
        <form className="learn-form" onSubmit={submit}>
          <textarea
            className="agent-input"
            rows={4}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={loading}
          />
          <button className="learn-button" type="submit" disabled={loading}>
            {loading ? "Routing…" : "Run orchestrator"}
          </button>
        </form>
        {error && <div className="error">{error}</div>}
        {result && (
          <div className="tutor-reply">
            <span className="history-mode">
              intent {result.intent} · tools {tools.join(", ") || "none"}
            </span>
            {result.summary && <p>{result.summary}</p>}
            {result.recommendation?.action && (
              <p>
                <em>Next best action:</em> {result.recommendation.action}
              </p>
            )}
            {result.results?.rag?.citations?.length > 0 && (
              <div className="citation-list">
                <strong>Document sources</strong>
                {result.results.rag.citations.map((c) => (
                  <div key={c.chunk_id} className="citation">
                    {c.filename}
                    {c.page_number ? ` — page ${c.page_number}` : ""}
                  </div>
                ))}
              </div>
            )}
            {result.results?.planner?.plan?.length > 0 && (
              <div className="path-list">
                {result.results.planner.plan.slice(0, 5).map((day, i) => (
                  <div key={i} className="history-item">
                    <strong>
                      Day {day.day}: {day.focus}
                    </strong>
                    {day.notes && <p>{day.notes}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

export default Agent;
