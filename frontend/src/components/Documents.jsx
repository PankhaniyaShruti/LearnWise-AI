import { useEffect, useState } from "react";
import { askRag, deleteDocument, listDocuments, uploadDocument } from "../api";

function Documents({ userEmail }) {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [asking, setAsking] = useState(false);

  useEffect(() => {
    if (userEmail) load();
  }, [userEmail]);

  async function load() {
    try {
      setLoading(true);
      setError("");
      const data = await listDocuments(userEmail);
      setDocs(data.items || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function onUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      setUploading(true);
      setError("");
      await uploadDocument(file, userEmail);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function remove(id) {
    try {
      await deleteDocument(id, userEmail);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function ask(event) {
    event.preventDefault();
    if (!question.trim()) return;
    try {
      setAsking(true);
      setError("");
      const data = await askRag(question.trim(), userEmail);
      setAnswer(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setAsking(false);
    }
  }

  return (
    <section className="dashboard-section">
      <div className="card">
        <p className="section-number">DOCUMENTS</p>
        <h2>Upload notes, then ask grounded questions</h2>
        <p className="quiz-subtitle">
          PDF or TXT is extracted, chunked, and indexed for you only. Answers cite the retrieved pages.
        </p>
        <label className="upload-label">
          <input type="file" accept=".pdf,.txt,application/pdf,text/plain" onChange={onUpload} disabled={uploading} />
          {uploading ? "Processing…" : "Choose PDF or TXT"}
        </label>
        {error && <div className="error">{error}</div>}
        {loading ? (
          <div className="history-loading">Loading documents…</div>
        ) : docs.length === 0 ? (
          <div className="history-empty">
            <h3>No documents yet</h3>
            <p>Upload lecture notes to enable grounded answers with citations.</p>
          </div>
        ) : (
          <div className="doc-list">
            {docs.map((doc) => (
              <div className="doc-row" key={doc.id}>
                <div>
                  <strong>{doc.filename}</strong>
                  <span className="history-mode">
                    {doc.file_type} · {doc.status} · {doc.size_bytes} bytes
                    {doc.metadata?.chunk_count ? ` · ${doc.metadata.chunk_count} chunks` : ""}
                  </span>
                </div>
                <button type="button" className="mode-button" onClick={() => remove(doc.id)}>
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <p className="section-number">GROUNDED ASK</p>
        <h2>Question your notes</h2>
        <form className="learn-form" onSubmit={ask}>
          <input
            className="topic-input"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. What does my notes say about overfitting?"
            disabled={asking}
          />
          <button className="learn-button" type="submit" disabled={asking || !docs.length}>
            {asking ? "Retrieving…" : "Ask from documents"}
          </button>
        </form>
        {answer && (
          <div className="tutor-reply">
            {answer.insufficient && <span className="history-mode">Insufficient source material</span>}
            <p>{answer.answer}</p>
            {answer.citations?.length > 0 && (
              <div className="citation-list">
                <strong>Sources</strong>
                {answer.citations.map((c) => (
                  <div key={c.chunk_id} className="citation">
                    {c.filename}
                    {c.page_number ? ` — page ${c.page_number}` : ""}
                    {typeof c.score === "number" ? ` · score ${c.score}` : ""}
                    {c.snippet ? <p>{c.snippet}</p> : null}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

export default Documents;
