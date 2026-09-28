import { useEffect, useState } from "react";
import { getHistory } from "../api";

// NAYA: userEmail prop accept kar rahe hain
function History({ userEmail }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (userEmail) {
      loadHistory();
    }
  }, [userEmail]);

  async function loadHistory() {
    try {
      setLoading(true);
      setError("");

      // NAYA: Backend ko userEmail bhej rahe hain
      const data = await getHistory(userEmail, 20);
      setHistory(data.items || []);
    } catch (err) {
      setError(err.message || "Failed to load learning history.");
    } finally {
      setLoading(false);
    }
  }

  function formatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "";
    }
    return date.toLocaleString();
  }

  if (loading) {
    return (
      <section className="card history-card">
        <p className="section-number">04 · LEARNING HISTORY</p>
        <h2>Your learning history</h2>
        <div className="history-loading">Loading your previous sessions...</div>
      </section>
    );
  }

  return (
    <section className="card history-card">
      <p className="section-number">04 · LEARNING HISTORY</p>
      <h2>Your learning history</h2>
      <p className="history-subtitle">
        Review the topics you have learned with LearnWise AI.
      </p>

      {error && <div className="error">{error}</div>}

      {!error && history.length === 0 && (
        <div className="history-empty">
          <h3>No learning sessions yet</h3>
          <p>Start learning a topic and it will appear here.</p>
        </div>
      )}

      {!error && history.length > 0 && (
        <div className="history-list">
          {history.map((item) => (
            <div className="history-item" key={item.id || item.session_id}>
              <div className="history-item-main">
                <h3>{item.topic}</h3>
                <span className="history-mode">{item.mode}</span>
              </div>

              {item.created_at && (
                <p className="history-date">{formatDate(item.created_at)}</p>
              )}

              {item.key_concepts?.length > 0 && (
                <div className="history-concepts">
                  {item.key_concepts.map((concept) => (
                    <span key={concept}>{concept}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <button className="retry-button" onClick={loadHistory} type="button">
        Refresh History
      </button>
    </section>
  );
}

export default History;