import { useState } from "react";
import { submitQuiz } from "../api";

function Quiz({ quiz, sessionId, userEmail }) {
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function selectAnswer(questionIndex, answer) {
    if (result) return;
    setAnswers((previous) => ({
      ...previous,
      [questionIndex]: answer,
    }));
  }

  async function handleSubmit() {
    if (Object.keys(answers).length !== quiz.length) {
      setError("Please answer all questions before submitting.");
      return;
    }
    try {
      setSubmitting(true);
      setError("");
      const formattedAnswers = quiz.map((_, questionIndex) => {
        const selected = answers[questionIndex];
        if (!selected) {
          throw new Error(`Missing answer for question ${questionIndex + 1}.`);
        }
        return {
          question_index: questionIndex,
          selected_answer: selected,
        };
      });
      const data = await submitQuiz(sessionId, formattedAnswers, userEmail);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  function retryQuiz() {
    setAnswers({});
    setResult(null);
    setError("");
  }

  if (!quiz?.length) return null;

  return (
    <div className="card quiz-card">
      <p className="section-number">03 · KNOWLEDGE CHECK</p>
      <h2>Test your understanding</h2>
      <p className="quiz-subtitle">Choose the best answer for each question.</p>

      {quiz.map((question, questionIndex) => {
        const selected = answers[questionIndex];

        return (
          <div className="question" key={questionIndex}>
            <div className="question-label">Question {questionIndex + 1}</div>
            <h3>{question.question}</h3>

            <div className="options">
              {question.options.map((option, optionIndex) => {
                const isSelected = selected === option;
                const isCorrect = result && option === question.correct_answer;
                const isWrong = result && isSelected && option !== question.correct_answer;

                let className = "option";
                if (isSelected) className += " selected";
                if (isCorrect) className += " correct";
                if (isWrong) className += " wrong";

                return (
                  <button
                    key={option}
                    className={className}
                    onClick={() => selectAnswer(questionIndex, option)}
                    disabled={Boolean(result)}
                    type="button"
                  >
                    <span className="option-letter">{String.fromCharCode(65 + optionIndex)}</span>
                    <span>{option}</span>
                  </button>
                );
              })}
            </div>

            {result && (
              <p className="answer">
                Correct answer: <strong>{question.correct_answer}</strong>
              </p>
            )}
          </div>
        );
      })}

      {error && <div className="error">{error}</div>}

      {!result ? (
        <button className="submit-quiz" onClick={handleSubmit} disabled={submitting} type="button">
          {submitting ? "Evaluating..." : "Check My Answers"}
        </button>
      ) : (
        <div className="quiz-result">
          <div className="score-number">{result.percentage}%</div>
          <h3>{result.performance}</h3>
          <p>
            You scored <strong>{result.score}/{result.total}</strong>
          </p>

          {result.weak_concepts?.length > 0 && (
            <div className="weak-result panel">
              <strong>Focus on:</strong>
              {result.weak_concepts.map((concept) => (
                <span key={concept}>{concept}</span>
              ))}
            </div>
          )}
          <button className="retry-button" onClick={retryQuiz} type="button">
            Try Again
          </button>
        </div>
      )}
    </div>
  );
}

export default Quiz;
