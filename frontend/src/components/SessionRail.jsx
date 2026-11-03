const ago = (iso) => {
  if (!iso) return "bez dát";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 15) return "živá";
  if (s < 3600) return `pred ${Math.round(s / 60) || 1} min`;
  if (s < 86400) return `pred ${Math.round(s / 3600)} h`;
  return new Date(iso).toLocaleDateString("sk-SK");
};

export const isLive = (session) => session?.last_ts && Date.now() - new Date(session.last_ts).getTime() < 15000;

export default function SessionRail({ sessions, selected, onSelect, user, onLogout, error }) {
  return (
    <aside className="rail">
      <header className="rail-head">
        <h1>Výškomer</h1>
        <p>{user.username} ({user.role === "admin" ? "admin" : "výskumník"})</p>
      </header>
      <nav aria-label="Relácie">
        {error && <p className="rail-note" role="alert">{error}</p>}
        {!error && sessions.length === 0 && (
          <p className="rail-note">Zatiaľ nie je žiadna relácia. Spusti simulátor alebo mock sender.</p>
        )}
        <ul>
          {sessions.map((s) => (
            <li key={s.id}>
              <button
                className={`rail-item ${s.id === selected ? "active" : ""}`}
                aria-current={s.id === selected ? "true" : undefined}
                onClick={() => onSelect(s.id)}
              >
                <span className="rail-name">{s.participant}</span>
                <span className={`rail-meta ${isLive(s) ? "live" : ""}`}>{ago(s.last_ts)}</span>
                <span className="rail-count">{s.samples} vzoriek</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>
      <button className="rail-logout" onClick={onLogout}>Odhlásiť sa</button>
    </aside>
  );
}
