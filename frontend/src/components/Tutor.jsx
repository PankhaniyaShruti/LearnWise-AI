import { useState } from "react";
import { askTutor } from "../api";

const ACTIONS = [
  { id: "explain_simply", label: "Explain Simply" },
  { id: "explain_with_analogy", label: "Analogy" },
  { id: "give_example", label: "Example" },
  { id: "explain_technically", label: "Technical" },
  { id: "give_hint", label: "Hint" },
  { id: "why_important", label: "Why Important?" },
  { id: "quiz_me", label: "Quiz Me" },
  { id: "still_dont_understand", label: "Still Don't Understand" },
];

function Tutor({ topic, concept, context, userEmail }) {
  const [reply, setReply] = useState("");
  const [strategy, setStrategy] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [previousStrategies, setPreviousStrategies] = useState([]);

  async function run(action) {
    try {
      setLoading(true);
      setError("");
      const data = await askTutor({
        topic,
        action,
        concept,
        context,
        previous_strategies: previousStrategies,
        userEmail,
      });
      setReply(data.reply);
      setStrategy(data.strategy || action);
      if (data.strategy) {
        setPreviousStrategies((prev) => [...prev.slice(-4), data.strategy]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card tutor-card">
      <p className="section-number">TUTOR</p>
      <h2>Ask your AI tutor</h2>
      <p className="quiz-subtitle">Get a different explanation style when something is unclear.</p>
      <div className="tutor-actions">
        {ACTIONS.map((a) => (
          <button key={a.id} type="button" className="mode-button" disabled={loading} onClick={() => run(a.id)}>
            {a.label}
          </button>
        ))}
      </div>
      {loading && <div className="history-loading">Tutor is thinking…</div>}
      {error && <div className="error">{error}</div>}
      {reply && (
        <div className="tutor-reply">
          {strategy && <span className="history-mode">{strategy}</span>}
          <p>{reply}</p>
        </div>
      )}
    </div>
  );
}

export default Tutor;
