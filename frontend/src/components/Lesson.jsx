function Lesson({ explanation, topic }) {
  if (!explanation) return null;

  const normalizedText = explanation.replace(/\\n/g, "\n");
  const lines = normalizedText
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  return (
    <section className="card lesson-card">
      <div className="section-number">01 · LESSON</div>
      <div className="lesson-header">
        <h2>{topic || "Your Lesson"}</h2>
      </div>
      <div className="lesson-content">
        {lines.map((line, index) => {
          if (line.startsWith("# ")) {
            return <h3 key={index}>{line.replace(/^#\s*/, "")}</h3>;
          }
          if (line.startsWith("## ")) {
            return <h4 key={index}>{line.replace(/^##\s*/, "")}</h4>;
          }
          if (/^\d+\.\s/.test(line)) {
            return (
              <div className="lesson-numbered" key={index}>
                <strong>{line.match(/^\d+/)?.[0]}.</strong>
                <p>{line.replace(/^\d+\.\s*/, "").replace(/\*\*/g, "")}</p>
              </div>
            );
          }
          if (line.startsWith("- ") || line.startsWith("* ")) {
            return (
              <div className="lesson-bullet" key={index}>
                <strong>•</strong>
                <p>{line.replace(/^[-*]\s*/, "").replace(/\*\*/g, "")}</p>
              </div>
            );
          }
          return <p key={index}>{line.replace(/\*\*/g, "")}</p>;
        })}
      </div>
    </section>
  );
}

export default Lesson;
