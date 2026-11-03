import { useCallback, useEffect, useState } from "react";
import { api, hasToken, setToken, setUnauthorizedHandler } from "./api.js";
import Login from "./components/Login.jsx";
import SessionRail from "./components/SessionRail.jsx";
import SessionView from "./components/SessionView.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(hasToken());
  const [sessions, setSessions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setSessions([]);
    setSelected(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    if (!hasToken()) return;
    api.me().then(setUser).catch(logout).finally(() => setChecking(false));
  }, [logout]);

  const refresh = useCallback(async () => {
    try {
      const list = await api.sessions();
      setSessions(list);
      setError("");
      setSelected((current) => current ?? list[0]?.id ?? null);
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    if (!user) return undefined;
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => clearInterval(timer);
  }, [user, refresh]);

  if (checking) return null;
  if (!user) return <Login onLogin={setUser} />;

  const session = sessions.find((s) => s.id === selected);
  return (
    <div className="app">
      <SessionRail
        sessions={sessions} selected={selected} onSelect={setSelected}
        user={user} onLogout={logout} error={error}
      />
      {session ? (
        <SessionView
          key={session.id} session={session} user={user}
          onErased={() => {
            setSelected(null);
            refresh();
          }}
        />
      ) : (
        <main className="view">
          <h1>Výškomer</h1>
          <p className="empty">Vyber reláciu vľavo. Keď simulátor začne posielať dáta, objaví sa tu živý prenos.</p>
        </main>
      )}
    </div>
  );
}
