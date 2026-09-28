import { useEffect, useState } from "react";
import { getProgress } from "../api";

// NAYA: userEmail prop accept kar rahe hain
function Progress({ userEmail }) {
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (userEmail) {
      loadProgress();
    }
  }, [userEmail]);

  async function loadProgress() {
    try {
      setLoading(true);
      setError("");

      // NAYA: Backend ko userEmail bhej rahe hain
      const data = await getProgress(userEmail);
      setProgress(data);
    } catch (err) {
      setError(err.message || "Failed to load progress.");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <section className="card progress-card">
        <p className="section-number">05 · YOUR PROGRESS</p>
        <h2>Learning progress</h2>
        <div className="progress-loading">Loading your progress...</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="card progress-card">
        <p className="section-number">05 · YOUR PROGRESS</p>
        <h2>Learning progress</h2>
        <div className="error">{error}</div>
        <button className="retry-button" onClick={loadProgress} type="button">
          Try Again
        </button>
      </section>
    );
  }

  const totalSessions = progress?.total_sessions ?? 0;
  const totalQuizAttempts = progress?.total_quiz_attempts ?? 0;
  const averageScore = progress?.average_score ?? 0;
  const bestScore = progress?.best_score ?? 0;

  return (
    <section className="card progress-card">
      <p className="section-number">05 · YOUR PROGRESS</p>
      <h2>Learning progress</h2>
      <p className="progress-subtitle">
        Track how consistently you are learning and testing your knowledge.
      </p>

      <div className="progress-grid">
        <div className="progress-stat">
          <span className="progress-stat-label">Topics Learned</span>
          <strong>{totalSessions}</strong>
        </div>
        <div className="progress-stat">
          <span className="progress-stat-label">Quiz Attempts</span>
          <strong>{totalQuizAttempts}</strong>
        </div>
        <div className="progress-stat">
          <span className="progress-stat-label">Average Score</span>
          <strong>{averageScore}%</strong>
        </div>
        <div className="progress-stat">
          <span className="progress-stat-label">Best Score</span>
          <strong>{bestScore}%</strong>
        </div>
      </div>

      {progress?.weak_concepts?.length > 0 && (
        <div className="progress-focus">
          <h3>Concepts to revisit</h3>
          <div className="weak-result">
            {progress.weak_concepts.map((concept) => (
              <span key={concept}>{concept}</span>
            ))}
          </div>
        </div>
      )}

      <button className="retry-button" onClick={loadProgress} type="button">
        Refresh Progress
      </button>
    </section>
  );
}

export default Progress;