import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { roleLabel } from "../lib/roles.js";

// Správa účtov pre admina. Člen je v zozname len pod pseudonymom, jeho meno server nevracia.
export default function UsersView() {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => api.users().then(setUsers).catch((e) => setError(e.message)), []);
  useEffect(() => {
    load();
  }, [load]);

  async function create(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setBusy(true);
    setError("");
    setNote("");
    try {
      const made = await api.createUser(data.get("username"), data.get("password"), data.get("role"));
      setNote(`Účet je vytvorený. V zozname ho nájdeš ako ${made.name}.`);
      form.reset();
      await load();
    } catch (e) {
      if (e.status === 409) setError("Účet s týmto menom už existuje.");
      else if (e.status === 422) setError("Meno má mať aspoň 3 znaky bez medzier a heslo aspoň 8 znakov.");
      else setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(user) {
    if (!window.confirm(`Zrušiť účet ${user.name}? Merania pod jeho pseudonymom ostanú, kým ich nevymažeš zvlášť.`)) return;
    try {
      await api.deleteUser(user.id);
      await load();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <main className="view">
      <header className="view-head">
        <div>
          <h1>Účty</h1>
          <p className="muted">Člen si po prihlásení pripojí svoj Oculus. V zozname je len pod pseudonymom.</p>
        </div>
      </header>

      {error && <p className="banner" role="alert">{error}</p>}

      <section className="analysis">
        <h2>Nový účet</h2>
        <form className="inline-form" onSubmit={create}>
          <label>
            Prihlasovacie meno
            <input name="username" required minLength={3} maxLength={64} autoComplete="off" />
          </label>
          <label>
            Heslo
            <input name="password" type="password" required minLength={8} autoComplete="new-password" />
          </label>
          <label>
            Rola
            <select name="role" defaultValue="member">
              <option value="member">člen</option>
              <option value="researcher">výskumník</option>
              <option value="admin">admin</option>
            </select>
          </label>
          <button type="submit" className="primary" disabled={busy}>Vytvoriť účet</button>
        </form>
        {note && <p className="note" role="status">{note}</p>}
      </section>

      <section className="analysis">
        <h2>Existujúce účty</h2>
        <div className="table-wrap">
          <table className="plain">
            <thead>
              <tr>
                <th scope="col">Účet</th>
                <th scope="col">Rola</th>
                <th scope="col"><span className="sr-only">Akcia</span></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <th scope="row">{u.name}</th>
                  <td>{roleLabel(u.role)}</td>
                  <td><button className="link" onClick={() => remove(u)}>Zrušiť účet</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
