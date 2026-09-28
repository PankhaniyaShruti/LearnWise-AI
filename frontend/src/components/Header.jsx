function Header({ currentView, onNavigate }) {
  return (
    <header className="header">
      <button
        className="logo"
        onClick={() => onNavigate("learn")}
        type="button"
      >
        LearnWise <span>AI</span>
      </button>

      <nav className="nav">
        <button
          className={currentView === "learn" ? "nav-link active" : "nav-link"}
          onClick={() => onNavigate("learn")}
          type="button"
        >
          Learn
        </button>

        <button
          className={
            currentView === "dashboard" ? "nav-link active" : "nav-link"
          }
          onClick={() => onNavigate("dashboard")}
          type="button"
        >
          Dashboard
        </button>

        <button
          className={
            currentView === "history" ? "nav-link active" : "nav-link"
          }
          onClick={() => onNavigate("history")}
          type="button"
        >
          History
        </button>

        <button
          className={
            currentView === "progress" ? "nav-link active" : "nav-link"
          }
          onClick={() => onNavigate("progress")}
          type="button"
        >
          Progress
        </button>
      </nav>

      <div className="header-status">
        <span className="status-dot" />
        AI Tutor
      </div>
    </header>
  );
}

export default Header;