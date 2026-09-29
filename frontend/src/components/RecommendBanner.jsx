import { useEffect, useState } from "react";
import { getRecommendation } from "../api";

const KIND_LABELS = {
  onboard: "START YOUR JOURNEY",
  prerequisite: "PREREQUISITE REVISION",
  critical: "PRIORITY REVISION",
  exam: "EXAM FOCUSED PRACTICE",
  rag_practice: "LEARN FROM YOUR NOTES",
  spaced: "SPACED REVISION",
  stretch: "CHALLENGE YOURSELF",
  default: "PERSONALIZED PRACTICE",
};

function RecommendBanner({ userEmail, goal }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

 useEffect(() => {
  if (!userEmail) {
    return;
  }

  let active = true;

  

    getRecommendation(userEmail, null, goal)
      .then((result) => {
        if (active) setData(result);
      })
      .catch((err) => {
        if (active) setError(err.message || "Something went wrong.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [userEmail, goal, retryKey]);

  if (!userEmail) return null;

  if (loading) {
    return (
      <section className="recommend-banner" aria-live="polite">
        <span className="eyebrow">YOUR LEARNING COACH</span>
        <p className="recommend-loading">
          Finding your next learning move...
        </p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="recommend-banner recommend-error" role="alert">
        <span className="eyebrow">YOUR LEARNING COACH</span>
        <h3>We couldn't load your recommendation.</h3>
        <p>{error}</p>
        <button
          type="button"
          className="recommend-retry"
          onClick={() => setRetryKey((key) => key + 1)}
        >
          Try again
        </button>
      </section>
    );
  }

  const rec = data?.recommendation;

  if (!rec) return null;

  const steps = Array.isArray(rec.steps) ? rec.steps : [];
  const label = KIND_LABELS[rec.kind] || "PERSONALIZED PRACTICE";

  return (
    <section className="recommend-banner" aria-live="polite">
      <div className="recommend-topline">
        <span className="eyebrow">YOUR LEARNING COACH</span>
        <span className="recommend-kind">{label}</span>
      </div>

      <h3 className="recommend-title">Your Next Learning Move</h3>

      {rec.focus_concept && (
        <div className="recommend-focus">
          <span>FOCUS CONCEPT</span>
          <strong>{rec.focus_concept}</strong>
        </div>
      )}

      <p className="recommend-action">{rec.action}</p>

      {rec.why && (
        <div className="recommend-why">
          <strong>Why this action?</strong>
          <p>{rec.why}</p>
        </div>
      )}

      {steps.length > 0 && (
        <div className="recommend-plan">
          <strong>Your action plan</strong>
          <ol>
            {steps.map((step, index) => (
              <li key={`${index}-${step}`}>{step}</li>
            ))}
          </ol>
        </div>
      )}

      {Number.isFinite(rec.exam_days_remaining) && (
        <div className="recommend-exam">
          <span>Exam countdown</span>
          <strong>
            {rec.exam_days_remaining === 0
              ? "Exam day"
              : `${rec.exam_days_remaining} days remaining`}
          </strong>
        </div>
      )}
    </section>
  );
}

export default RecommendBanner;