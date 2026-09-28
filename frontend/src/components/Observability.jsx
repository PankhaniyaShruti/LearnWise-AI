import { useEffect, useState } from "react";
import { getObservability } from "../api";

function Observability({ userEmail }) {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userEmail) return;
    setLoading(true);
    getObservability(userEmail)
      .then((data) => setItems(data.items || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [userEmail]);

  return (
    <section className="dashboard-section">
      <div className="card">
        <p className="section-number">LLMOPS</p>
        <h2>Your AI request log</h2>
        <p className="quiz-subtitle">
          Latency, tokens, prompt version, and success — without storing prompts or document text.
        </p>
        {loading && <div className="history-loading">Loading events…</div>}
        {error && <div className="error">{error}</div>}
        {!loading && items.length === 0 && (
          <div className="history-empty">
            <h3>No events yet</h3>
            <p>Generate a lesson or ask a question to record an observability event.</p>
          </div>
        )}
        <div className="obs-table">
          {items.map((e) => (
            <div className="obs-row" key={e.id}>
              <strong>{e.feature}</strong>
              <span>
                {e.prompt_name}@{e.prompt_version || "—"}
              </span>
              <span>{e.model || "—"}</span>
              <span>{e.latency_ms != null ? `${e.latency_ms} ms` : "—"}</span>
              <span>{e.total_tokens != null ? `${e.total_tokens} tok` : "—"}</span>
              <span>{e.success ? "ok" : e.error_type || "failed"}</span>
              <span>{e.rag_used ? `rag ${e.retrieved_chunks || 0}` : ""}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default Observability;
