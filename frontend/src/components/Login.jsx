import { useState } from "react";
import { api, setToken } from "../api.js";
import { Mark } from "./SessionRail.jsx";

export default function Login({ onLogin }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      const res = await api.login(form.get("username"), form.get("password"));
      setToken(res.access_token);
      onLogin({ username: form.get("username"), role: res.role });
    } catch (e) {
      setError(e.status === 401 ? "Nesprávne meno alebo heslo." : "Server neodpovedá. Skontroluj, či beží API.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login">
      <form onSubmit={submit} className="login-form">
        <div className="brand">
          <Mark />
          <strong>Výškomer</strong>
        </div>
        <p>Sledovanie tepu a pohybu účastníka vo VR simulátore výšky.</p>
        <label>
          Meno
          <input name="username" autoComplete="username" required autoFocus />
        </label>
        <label>
          Heslo
          <input name="password" type="password" autoComplete="current-password" required />
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button type="submit" className="primary" disabled={busy}>{busy ? "Prihlasujem" : "Prihlásiť sa"}</button>
      </form>
    </main>
  );
}
