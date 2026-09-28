import { useEffect, useState } from "react";
import { getRecommendation } from "../api";

function RecommendBanner({ userEmail, goal }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!userEmail) return;
    getRecommendation(userEmail, null, goal)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [userEmail, goal]);

  if (error) return null;
  const rec = data?.recommendation;
  if (!rec) return null;

  return (
    <div className="recommend-banner">
      <span className="eyebrow">NEXT BEST ACTION</span>
      <h3>{rec.action}</h3>
      <p>{rec.why}</p>
      {rec.steps?.length > 0 && (
        <ol>
          {rec.steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      )}
    </div>
  );
}

export default RecommendBanner;
