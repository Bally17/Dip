const ago = (iso) => {
  if (!iso) return "bez dát";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 15) return "živá";
  if (s < 3600) return `pred ${Math.round(s / 60) || 1} min`;
  if (s < 86400) return `pred ${Math.round(s / 3600)} h`;
  return new Date(iso).toLocaleDateString("sk-SK");
};

export const isLive = (session) => session?.last_ts && Date.now() - new Date(session.last_ts).getTime() < 15000;

// Značka: zvislá stupnica s jednou zvýraznenou ryskou, výškomer v skratke.
export function Mark({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" aria-hidden="true">
      <rect width="28" height="28" rx="6" fill="#1d1f20" />
      <path d="M9 7h10M9 12h6M9 17h10M9 22h6" stroke="#9aa1a9" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M9 12h6" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

export default function SessionRail({ sessions, selected, onSelect, user, onLogout, error }) {
  return (
    <aside className="rail">
      <div className="brand">
        <Mark />
        <strong>Výškomer</strong>
      </div>
      <p className="scope">Štúdia strachu z výšky</p>
      <nav aria-label="Relácie">
        <p className="group-label">Relácie</p>
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
                <span className="rail-count num">{s.samples} vzoriek</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>
      <div className="rail-user">
        <span>{user.username} ({user.role === "admin" ? "admin" : "výskumník"})</span>
        <button onClick={onLogout}>Odhlásiť sa</button>
      </div>
    </aside>
  );
}
