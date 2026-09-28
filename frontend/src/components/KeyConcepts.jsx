function KeyConcepts({ concepts = [] }) {
  return (
    <section className="card concepts-card">
      <div className="section-number">02 — KEY IDEAS</div>
      <h2>Key Concepts</h2>
      <div className="concepts">
        {concepts.map((concept, index) => (
          <div className="concept" key={`${concept}-${index}`}>
            <span>{index + 1}</span>
            <p>{concept}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default KeyConcepts;