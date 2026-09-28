import { useEffect, useState } from "react";
import { getKnowledgeGraph } from "../api";

function KnowledgeGraphPanel() {
  const [graph, setGraph] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getKnowledgeGraph()
      .then(setGraph)
      .catch((err) => setError(err.message));
  }, []);

  const concepts = graph?.concepts || [];
  const rels = graph?.relationships || [];
  const byId = Object.fromEntries(concepts.map((c) => [c.id, c.name]));

  return (
    <div className="card">
      <p className="section-number">KNOWLEDGE GRAPH</p>
      <h2>Concepts and prerequisites</h2>
      {error && <div className="error">{error}</div>}
      <p className="quiz-subtitle">
        {concepts.length} concepts · {rels.length} relationships. Used for prerequisite gaps and learning paths.
      </p>
      <div className="kg-list">
        {rels.slice(0, 18).map((r) => (
          <div className="kg-edge" key={r.id}>
            <span>{byId[r.source_id] || r.source_id}</span>
            <em>{r.relation}</em>
            <span>{byId[r.target_id] || r.target_id}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default KnowledgeGraphPanel;
