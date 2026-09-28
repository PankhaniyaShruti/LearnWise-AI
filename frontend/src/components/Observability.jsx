import { useEffect, useState } from "react";
import { getObservability } from "../api";

function Observability({ userEmail }) {
  const [result, setResult] = useState({
    email: null,
    items: [],
    error: "",
    loading: false,
  });

  useEffect(() => {
    if (!userEmail) return;

    let cancelled = false;

    Promise.resolve()
      .then(() => {
        if (cancelled) return null;

        setResult({
          email: userEmail,
          items: [],
          error: "",
          loading: true,
        });

        return getObservability(userEmail);
      })
      .then((data) => {
        if (cancelled || !data) return;

        setResult({
          email: userEmail,
          items: data.items || [],
          error: "",
          loading: false,
        });
      })
      .catch((err) => {
        if (cancelled) return;

        setResult({
          email: userEmail,
          items: [],
          error: err.message || "Failed to load events.",
          loading: false,
        });
      });

    return () => {
      cancelled = true;
    };
  }, [userEmail]);

  const isCurrentUser = result.email === userEmail;
  const items = isCurrentUser ? result.items : [];
  const error = isCurrentUser ? result.error : "";
  const loading = Boolean(userEmail) &&
    (!isCurrentUser || result.loading);

  return (
    <section className="dashboard-section">
      <div className="card">
        <p className="section-number">LLMOPS</p>
        <h2>Your AI request log</h2>

        <p className="quiz-subtitle">
          Latency, tokens, prompt version, and success — without storing prompts or document text.
        </p>

        {loading && (
          <div className="history-loading">Loading events…</div>
        )}

        {error && <div className="error">{error}</div>}

        {!loading && !error && items.length === 0 && (
          <div className="history-empty">
            <h3>No events yet</h3>
            <p>
              Generate a lesson or ask a question to record an observability event.
            </p>
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

              <span>
                {e.latency_ms != null ? `${e.latency_ms} ms` : "—"}
              </span>

              <span>
                {e.total_tokens != null ? `${e.total_tokens} tok` : "—"}
              </span>

              <span>
                {e.success ? "ok" : e.error_type || "failed"}
              </span>

              <span>
                {e.rag_used ? `rag ${e.retrieved_chunks || 0}` : ""}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default Observability;