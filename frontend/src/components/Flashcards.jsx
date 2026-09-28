import { useState } from "react";
import { generateFlashcards } from "../api";

function Flashcards({ topic, concepts, userEmail }) {
  const [cards, setCards] = useState([]);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [known, setKnown] = useState({});

  async function load() {
    try {
      setLoading(true);
      setError("");
      const data = await generateFlashcards(topic, concepts || [], userEmail);
      setCards(data.cards || []);
      setIndex(0);
      setFlipped(false);
      setKnown({});
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (!topic) return null;
  const card = cards[index];

  return (
    <div className="card flashcard-panel">
      <p className="section-number">FLASHCARDS</p>
      <h2>Review with cards</h2>
      {!cards.length ? (
        <button className="submit-quiz" type="button" onClick={load} disabled={loading}>
          {loading ? "Generating…" : "Generate flashcards"}
        </button>
      ) : (
        <>
          <div
            className={`flashcard ${flipped ? "flipped" : ""}`}
            onClick={() => setFlipped(!flipped)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && setFlipped(!flipped)}
          >
            <div className="flashcard-inner">
              <strong>{flipped ? "Answer" : "Question"}</strong>
              <p>{flipped ? card.back : card.front}</p>
              {card.concept && <span className="history-mode">{card.concept}</span>}
            </div>
          </div>
          <div className="flashcard-nav">
            <button type="button" className="mode-button" disabled={index === 0} onClick={() => { setIndex(index - 1); setFlipped(false); }}>
              Previous
            </button>
            <button type="button" className="mode-button" onClick={() => setKnown({ ...known, [index]: true })}>
              Known
            </button>
            <button type="button" className="mode-button" onClick={() => setKnown({ ...known, [index]: false })}>
              Needs revision
            </button>
            <button type="button" className="mode-button" disabled={index >= cards.length - 1} onClick={() => { setIndex(index + 1); setFlipped(false); }}>
              Next
            </button>
          </div>
          <p className="quiz-subtitle">
            Card {index + 1} / {cards.length}
            {known[index] === true && " · marked known"}
            {known[index] === false && " · needs revision"}
          </p>
        </>
      )}
      {error && <div className="error">{error}</div>}
    </div>
  );
}

export default Flashcards;
