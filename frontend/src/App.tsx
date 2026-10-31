export default function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1 className="app-title">NoBluff</h1>
        <p className="app-tagline">
          Evidence-based issue and pull request triage
        </p>
      </header>
      <main className="app-main">
        <section className="intro-card">
          <h2>Technical Claim Verification</h2>
          <p>
            NoBluff helps open-source maintainers check technical claims in issues and
            pull requests against repository source code and documentation.
          </p>
        </section>
      </main>
    </div>
  );
}
