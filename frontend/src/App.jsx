import { useCallback, useEffect, useState } from "react";
import { api, hasToken, setToken, setUnauthorizedHandler } from "./api.js";
import { can } from "./lib/roles.js";

// V ukážke (?demo) sa dá stránka otvoriť priamo, napr. ?demo=member&page=device.
const startPage = (import.meta.env.DEV && new URLSearchParams(window.location.search).get("page")) || "sessions";
import DeviceView from "./components/DeviceView.jsx";
import Login from "./components/Login.jsx";
import SessionRail from "./components/SessionRail.jsx";
import SessionView from "./components/SessionView.jsx";
import UsersView from "./components/UsersView.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(hasToken());
  const [sessions, setSessions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [page, setPage] = useState(startPage);
  const [error, setError] = useState("");

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setSessions([]);
    setSelected(null);
    setPage("sessions");
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
        sessions={sessions} selected={page === "sessions" ? selected : null}
        onSelect={(id) => {
          setSelected(id);
          setPage("sessions");
        }}
        page={page} onPage={setPage}
        user={user} onLogout={logout} error={error}
      />
      {page === "users" && can(user.role, "manageUsers") ? (
        <UsersView />
      ) : page === "device" && can(user.role, "pairDevice") ? (
        <DeviceView user={user} onAccountDeleted={logout} />
      ) : session ? (
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
          {can(user.role, "pairDevice") && sessions.length === 0 ? (
            <>
              <p className="empty">Zatiaľ nemáš žiadne meranie. Najprv spáruj svoj Oculus, potom spusti simulátor.</p>
              <button className="primary" onClick={() => setPage("device")}>Pripojiť Oculus</button>
            </>
          ) : (
            <p className="empty">Vyber reláciu vľavo. Keď simulátor začne posielať dáta, objaví sa tu živý prenos.</p>
          )}
        </main>
      )}
    </div>
  );
}
