import { useCallback, useEffect, useState } from "react";
import {
  getMasteryPredictions,
  getProgress,
  startAdaptivePractice,
  startRevision,
} from "../api";

function Dashboard({ userEmail, onOpenLesson }) {
  const [data, setData] = useState(null);
  const [ml, setMl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    if (!userEmail) return;

    try {
      const d = await getProgress(userEmail);

      setData(d);
      setError("");

      if (d?.mastery?.total_concepts) {
        try {
          const predictions = await getMasteryPredictions(userEmail);
          setMl(predictions);
        } catch {
          setMl(null);
        }
      } else {
        setMl(null);
      }
    } catch (err) {
      setError(err.message || "Failed to load dashboard.");
    } finally {
      setLoading(false);
    }
  }, [userEmail]);

  useEffect(() => {
    if (!userEmail) return;

    let active = true;

    const loadInitialDashboard = async () => {
      try {
        const d = await getProgress(userEmail);

        if (!active) return;

        setData(d);
        setError("");

        if (d?.mastery?.total_concepts) {
          try {
            const predictions = await getMasteryPredictions(userEmail);

            if (active) setMl(predictions);
          } catch {
            if (active) setMl(null);
          }
        } else {
          setMl(null);
        }
      } catch (err) {
        if (active) {
          setError(err.message || "Failed to load dashboard.");
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    loadInitialDashboard();

    return () => {
      active = false;
    };
  }, [userEmail]);

  const refreshDashboard = async () => {
    setLoading(true);
    await load();
  };

  async function revise() {
    try {
      setBusy("revision");

      const lesson = await startRevision(userEmail);
      onOpenLesson?.(lesson);

      await refreshDashboard();
    } catch (err) {
      setError(err.message || "Failed to start revision.");
    } finally {
      setBusy("");
    }
  }

  async function practice(difficulty) {
    try {
      setBusy(difficulty);

      const topic =
        data?.mastery?.weak_concepts?.[0]?.topic ||
        data?.mastery?.concepts?.[0]?.topic ||
        "photosynthesis";

      const lesson = await startAdaptivePractice(
        topic,
        difficulty,
        userEmail
      );

      onOpenLesson?.(lesson);

      await refreshDashboard();
    } catch (err) {
      setError(err.message || "Failed to start adaptive practice.");
    } finally {
      setBusy("");
    }
  }

  if (loading) {
    return (
      <section className="card progress-card">
        <p className="section-number">05 · DASHBOARD</p>
        <h2>Learning dashboard</h2>
        <div className="progress-loading">Loading your dashboard…</div>
      </section>
    );
  }

  const mastery = data?.mastery || {};
  const concepts = mastery.concepts || [];
  const recommendations = mastery.recommendations || [];
  const achievements = data?.achievements || [];

  return (
    <section className="card progress-card dashboard-card">
      <p className="section-number">05 · DASHBOARD</p>
      <h2>Learning dashboard</h2>

      <p className="progress-subtitle">
        Mastery, weak areas, and personalized next steps — from your real activity.
      </p>

      {error && <div className="error">{error}</div>}

      <div className="progress-grid">
        <div className="progress-stat">
          <span className="progress-stat-label">Overall Mastery</span>
          <strong>{mastery.overall_mastery ?? 0}%</strong>
        </div>

        <div className="progress-stat">
          <span className="progress-stat-label">Concepts</span>
          <strong>{mastery.total_concepts ?? 0}</strong>
        </div>

        <div className="progress-stat">
          <span className="progress-stat-label">Topics / Sessions</span>
          <strong>{data?.total_sessions ?? 0}</strong>
        </div>

        <div className="progress-stat">
          <span className="progress-stat-label">Quiz Attempts</span>
          <strong>{data?.total_quiz_attempts ?? 0}</strong>
        </div>

        <div className="progress-stat">
          <span className="progress-stat-label">Average Score</span>
          <strong>{data?.average_score ?? 0}%</strong>
        </div>

        <div className="progress-stat">
          <span className="progress-stat-label">Best Score</span>
          <strong>{data?.best_score ?? 0}%</strong>
        </div>

        <div className="progress-stat">
          <span className="progress-stat-label">Streak</span>
          <strong>{data?.streak_days ?? 0}d</strong>
        </div>
      </div>

      <div className="dashboard-actions">
        <button
          className="submit-quiz"
          type="button"
          onClick={revise}
          disabled={!!busy}
        >
          {busy === "revision" ? "Building revision…" : "Revise My Weak Areas"}
        </button>

        <button
          className="mode-button"
          type="button"
          onClick={() => practice("easy")}
          disabled={!!busy}
        >
          Adaptive: Easy
        </button>

        <button
          className="mode-button"
          type="button"
          onClick={() => practice("medium")}
          disabled={!!busy}
        >
          Adaptive: Medium
        </button>

        <button
          className="mode-button"
          type="button"
          onClick={() => practice("hard")}
          disabled={!!busy}
        >
          Adaptive: Hard
        </button>
      </div>

      {ml?.predictions?.length > 0 && (
        <div className="progress-focus">
          <h3>ML mastery prediction</h3>
          <p className="quiz-subtitle">{ml.disclaimer}</p>

          {ml.predictions.slice(0, 6).map((p) => (
            <div key={p.concept} className="recommendation-item">
              <strong>{p.concept}</strong>
              <span className="history-mode">
                {p.predicted_label} · p={p.mastery_probability}
                {p.rule_mastery_score != null
                  ? ` · rule ${p.rule_mastery_score}%`
                  : ""}
              </span>
            </div>
          ))}
        </div>
      )}

      {recommendations.length > 0 && (
        <div className="progress-focus">
          <h3>AI recommendations</h3>

          {recommendations.map((r) => (
            <div key={r.concept} className="recommendation-item">
              <strong>{r.concept}</strong>

              <span className="history-mode">
                {r.mastery_label} · {r.mastery_score}%
              </span>

              <p>
                <em>Why:</em> {r.why}
              </p>

              <p>
                <em>What to do:</em> {r.what_to_do}
              </p>

              <p>
                <em>Next:</em> {r.next_step}
              </p>
            </div>
          ))}
        </div>
      )}

      {concepts.length > 0 && (
        <div className="progress-focus">
          <h3>Concept mastery</h3>

          <div className="mastery-list">
            {concepts.map((c) => (
              <div key={c.id || c.concept} className="mastery-row">
                <div className="mastery-meta">
                  <strong>{c.concept}</strong>
                  <span>{c.mastery_label}</span>
                </div>

                <div className="mastery-bar">
                  <div
                    className="mastery-fill"
                    style={{ width: `${c.mastery_score}%` }}
                  />
                </div>

                <span className="mastery-score">{c.mastery_score}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {achievements.length > 0 && (
        <div className="progress-focus">
          <h3>Achievements</h3>

          <div className="achievement-list">
            {achievements.map((a) => (
              <div key={a.id} className="achievement-chip">
                <strong>{a.title}</strong>
                <span>{a.description}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        className="retry-button"
        onClick={refreshDashboard}
        type="button"
      >
        Refresh Dashboard
      </button>
    </section>
  );
}

export default Dashboard;