import { useEffect, useState } from "react";
import { supabase, supabaseConfigured } from "./supabase";
import { generateLearningPath, learnTopic } from "./api";

import Agent from "./components/Agent";
import Dashboard from "./components/Dashboard";
import Documents from "./components/Documents";
import Flashcards from "./components/Flashcards";
import History from "./components/History";
import KeyConcepts from "./components/KeyConcepts";
import KnowledgeGraphPanel from "./components/KnowledgeGraphPanel";
import Lesson from "./components/Lesson";
import Observability from "./components/Observability";
import Quiz from "./components/Quiz";
import RecommendBanner from "./components/RecommendBanner";
import Tutor from "./components/Tutor";

import "./App.css";

function getOrCreateGuestEmail() {
  const key = "learnwise_guest_id";
  let id = localStorage.getItem(key);
  if (!id) {
    id =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `guest-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem(key, id);
  }
  return `guest-${id}@learnwise.local`;
}

function App() {
  const [session, setSession] = useState(null);
  const [guestMode, setGuestMode] = useState(!supabaseConfigured);
  const [guestEmail, setGuestEmail] = useState(() => (!supabaseConfigured ? getOrCreateGuestEmail() : ""));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoginView, setIsLoginView] = useState(true);
  const [authMessage, setAuthMessage] = useState("");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);

  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem("learnwise_theme") === "dark" ? "dark" : "light";
    } catch {
      return "light";
    }
  });
  const [topic, setTopic] = useState("");
  const [mode, setMode] = useState("simple");
  const [lesson, setLesson] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [view, setView] = useState("learn");

  useEffect(() => {
    if (!supabaseConfigured) return undefined;
    supabase.auth.getSession().then(({ data: { session: next } }) => {
      setSession(next);
    });
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      if (next) {
        setGuestMode(false);
        setGuestEmail("");
      }
    });
    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("learnwise_theme", theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  function toggleTheme() {
    setTheme(theme === "light" ? "dark" : "light");
  }

  async function handleAuth(e) {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError("");
    setAuthMessage("");
    if (isLoginView) {
      const { error: err } = await supabase.auth.signInWithPassword({ email, password });
      if (err) setAuthError(err.message);
    } else {
      const { error: err } = await supabase.auth.signUp({ email, password });
      if (err) setAuthError(err.message);
      else {
        setAuthMessage("Success! Check your email for the verification link.");
        setEmail("");
        setPassword("");
      }
    }
    setAuthLoading(false);
  }

  async function handleSignOut() {
    setGuestMode(false);
    setGuestEmail("");
    setLesson(null);
    if (supabaseConfigured) await supabase.auth.signOut();
    if (!supabaseConfigured) {
      setGuestEmail(getOrCreateGuestEmail());
      setGuestMode(true);
    }
  }

  function continueAsGuest() {
    const ge = getOrCreateGuestEmail();
    setGuestEmail(ge);
    setGuestMode(true);
    setAuthError("");
    setAuthMessage("");
    setLesson(null);
  }

  async function handleLearn(event) {
    event.preventDefault();
    const trimmedTopic = topic.trim();
    if (!trimmedTopic) {
      setError("Tell me what you want to learn first.");
      return;
    }
    try {
      setLoading(true);
      setError("");
      setLesson(null);
      const userEmail = session?.user?.email || guestEmail;
      if (!userEmail) throw new Error("No user identity. Sign in or continue as guest.");
      const data = await learnTopic(trimmedTopic, mode, userEmail);
      if (!data.session_id) throw new Error("Server did not return a session_id.");
      setLesson({ ...data, topic: data.topic || trimmedTopic, mode: data.mode || mode });
      setView("learn");
      setTimeout(() => {
        document.querySelector(".learning-result")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
    } catch (err) {
      setError(err.message || "Something went wrong while creating your lesson.");
    } finally {
      setLoading(false);
    }
  }

  const isAuthenticated = Boolean(session) || guestMode;

  if (!isAuthenticated) {
    return (
      <div className="login-screen">
        <div className="login-box">
          <div className="login-brand">
            <span className="brand-mark">LW</span>
            <span className="brand-name">LearnWise</span>
          </div>
          <h1>{isLoginView ? "Welcome back." : "Create your account."}</h1>
          <p className="login-subtitle">
            {isLoginView
              ? "Sign in to access your personalized learning studio."
              : "Sign up to start learning with AI. We will send a verification link to your email."}
          </p>
          {supabaseConfigured && (
            <form onSubmit={handleAuth} className="login-form">
              <div className="input-group">
                <label>Email Address</label>
                <input
                  className="login-input"
                  type="email"
                  placeholder="e.g. you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              <div className="input-group">
                <label>Password</label>
                <input
                  className="login-input"
                  type="password"
                  placeholder="Minimum 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                />
              </div>
              {authError && <div className="error">{authError}</div>}
              {authMessage && <div className="success-note">{authMessage}</div>}
              <button className="login-btn" type="submit" disabled={authLoading}>
                {authLoading ? "Please wait..." : isLoginView ? "Sign In" : "Sign Up"}
              </button>
            </form>
          )}
          <button type="button" className="login-btn ghost" onClick={continueAsGuest}>
            Continue as Guest
          </button>
          <p className="hint">Guest mode is for local testing. Progress is tied to this browser.</p>
          {supabaseConfigured && (
            <p className="login-footer-text">
              {isLoginView ? "Don't have an account? " : "Already have an account? "}
              <button
                type="button"
                className="text-link"
                onClick={() => {
                  setIsLoginView(!isLoginView);
                  setAuthError("");
                  setAuthMessage("");
                }}
              >
                {isLoginView ? "Sign up here" : "Sign in here"}
              </button>
            </p>
          )}
        </div>
      </div>
    );
  }

  const userEmail = session?.user?.email || guestEmail;
  const nav = [
    ["learn", "Learn"],
    ["documents", "Documents"],
    ["agent", "Agent"],
    ["dashboard", "Dashboard"],
    ["ops", "Ops"],
  ];

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <a className="brand" href="/">
            <span className="brand-mark">LW</span>
            <span className="brand-name">LearnWise</span>
          </a>
          <nav className="main-nav">
            {nav.map(([id, label]) => (
              <button
                key={id}
                type="button"
                className={view === id ? "nav-link active" : "nav-link"}
                onClick={() => setView(id)}
              >
                {label}
              </button>
            ))}
          </nav>
          <div className="topbar-right">
            <span title={userEmail}>{guestMode ? "Guest" : userEmail}</span>
            <button className="theme-toggle" onClick={toggleTheme} type="button">
              {theme === "light" ? "Dark Mode" : "Light Mode"}
            </button>
            <button className="theme-toggle danger" onClick={handleSignOut} type="button">
              {guestMode ? "Exit Guest" : "Log Out"}
            </button>
          </div>
        </div>
      </header>

      <main className="container">
        {view === "learn" && (
          <>
            <section className="hero">
              <div className="hero-copy">
                <div className="eyebrow">ADAPTIVE LEARNING INTELLIGENCE</div>
                <h1>
                  Learn something <br />
                  <em>worth knowing.</em>
                </h1>
                <p className="hero-description">
                  Lessons, diagnostics, mastery, grounded notes, and a routed learning agent — from your real activity.
                </p>
              </div>
              <RecommendBanner userEmail={userEmail} goal={topic} />
              <div className="learning-box">
                <form className="learn-form" onSubmit={handleLearn}>
                  <div className="input-row">
                    <div className="input-wrapper">
                      <input
                        className="topic-input"
                        type="text"
                        value={topic}
                        onChange={(e) => setTopic(e.target.value)}
                        placeholder="e.g. How does logistic regression work?"
                        disabled={loading}
                      />
                      {topic && (
                        <button type="button" className="clear-input" onClick={() => setTopic("")}>
                          ×
                        </button>
                      )}
                    </div>
                    <button className="learn-button" type="submit" disabled={loading}>
                      {loading ? "Building..." : "Start learning"}
                    </button>
                  </div>
                  <div className="learning-options">
                    <div className="mode-area">
                      <div className="mode-selector">
                        {["simple", "detailed", "study", "story", "exam", "practical"].map((m) => (
                          <button
                            key={m}
                            type="button"
                            className={mode === m ? "mode-button active" : "mode-button"}
                            onClick={() => setMode(m)}
                            disabled={loading}
                          >
                            {m.charAt(0).toUpperCase() + m.slice(1)}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </form>
                {error && (
                  <div className="error">
                    <span>!</span> {error}
                  </div>
                )}
              </div>
            </section>

            {lesson && (
              <section className="learning-result">
                <div className="result-heading">
                  <div>
                    <span className="result-kicker">YOUR SESSION</span>
                    <h2>
                      Let's understand <em>{lesson.topic || topic}</em>
                    </h2>
                  </div>
                </div>
                <Lesson explanation={lesson.explanation} topic={lesson.topic || topic} />
                <KeyConcepts concepts={lesson.key_concepts} />
                <Quiz quiz={lesson.quiz} sessionId={lesson.session_id} userEmail={userEmail} />
                <Tutor
                  topic={lesson.topic || topic}
                  concept={(lesson.key_concepts || [])[0]}
                  context={lesson.explanation}
                  userEmail={userEmail}
                />
                <Flashcards topic={lesson.topic || topic} concepts={lesson.key_concepts || []} userEmail={userEmail} />
              </section>
            )}
            <AdvancedTools userEmail={userEmail} />
          </>
        )}

        {view === "documents" && <Documents userEmail={userEmail} />}
        {view === "agent" && <Agent userEmail={userEmail} topic={topic || lesson?.topic} />}
        {view === "dashboard" && (
          <section className="dashboard-section">
            <RecommendBanner userEmail={userEmail} goal={topic} />
            <div className="dashboard-grid">
              <History userEmail={userEmail} />
              <Dashboard
                userEmail={userEmail}
                onOpenLesson={(data) => {
                  setLesson({ ...data, topic: data.topic, mode: data.mode || data.difficulty || "practice" });
                  setView("learn");
                  setTimeout(() => {
                    document.querySelector(".learning-result")?.scrollIntoView({ behavior: "smooth", block: "start" });
                  }, 100);
                }}
              />
            </div>
            <KnowledgeGraphPanel />
          </section>
        )}
        {view === "ops" && <Observability userEmail={userEmail} />}
      </main>
    </div>
  );
}

function AdvancedTools({ userEmail }) {
  const [pathTopic, setPathTopic] = useState("");
  const [path, setPath] = useState(null);
  const [pathLoading, setPathLoading] = useState(false);
  const [pathError, setPathError] = useState("");

  async function buildPath(e) {
    e.preventDefault();
    if (!pathTopic.trim()) return;
    try {
      setPathLoading(true);
      setPathError("");
      setPath(await generateLearningPath(pathTopic.trim(), userEmail));
    } catch (err) {
      setPathError(err.message);
    } finally {
      setPathLoading(false);
    }
  }

  return (
    <section className="dashboard-section">
      <div className="dashboard-grid">
        <div className="card">
          <p className="section-number">LEARNING PATH</p>
          <h2>Break a topic into steps</h2>
          <form onSubmit={buildPath} className="learn-form">
            <input
              className="topic-input"
              value={pathTopic}
              onChange={(e) => setPathTopic(e.target.value)}
              placeholder="e.g. Machine Learning"
            />
            <button className="learn-button" type="submit" disabled={pathLoading}>
              {pathLoading ? "Building…" : "Create path"}
            </button>
          </form>
          {pathError && <div className="error">{pathError}</div>}
          {path?.items?.length > 0 && (
            <ol className="path-list">
              {path.items.map((item, i) => (
                <li key={i}>
                  <strong>{item.title}</strong>
                  <p>{item.description}</p>
                </li>
              ))}
            </ol>
          )}
        </div>

      </div>
    </section>
  );
}

export default App;
