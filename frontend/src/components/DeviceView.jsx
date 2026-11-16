import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { countdown, deviceStatus, spacedCode } from "../lib/pairing.js";

const nowS = () => Date.now() / 1000;

// Stránka člena: spárovanie Oculusu s účtom, zoznam jeho headsetov a vymazanie vlastných údajov.
export default function DeviceView({ user, onAccountDeleted }) {
  const [devices, setDevices] = useState([]);
  const [code, setCode] = useState(null);
  const [now, setNow] = useState(nowS);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  const load = useCallback(() => api.devices().then(setDevices).catch((e) => setError(e.message)), []);

  useEffect(() => {
    load();
    const poll = setInterval(load, 3000);
    const tick = setInterval(() => setNow(nowS()), 1000);
    return () => {
      clearInterval(poll);
      clearInterval(tick);
    };
  }, [load]);

  const left = code ? countdown(code.expiresAt, now) : null;

  async function newCode() {
    setError("");
    setNote("");
    try {
      const res = await api.pairingCode();
      setCode({ value: res.code, expiresAt: nowS() + res.expires_in_s, known: devices.length });
    } catch (e) {
      setError(e.message);
    }
  }

  // Keď pribudne headset, kód už splnil účel.
  useEffect(() => {
    if (code && devices.length > code.known) {
      setCode(null);
      setNote("Oculus je spárovaný. Merania z neho uvidíš v časti Relácie.");
    }
  }, [devices, code]);

  async function disconnect(device) {
    if (!window.confirm("Odpojiť tento headset? Ak ho budeš chcieť znova používať, treba ho spárovať novým kódom.")) return;
    try {
      await api.disconnectDevice(device.id);
      await load();
    } catch (e) {
      setError(e.message);
    }
  }

  async function eraseData() {
    if (!window.confirm("Vymazať všetky tvoje merania? Nedá sa to vrátiť.")) return;
    try {
      const res = await api.eraseMyData();
      setNote(res.erased ? "Tvoje merania sú vymazané." : "Nemáš žiadne merania na vymazanie.");
    } catch (e) {
      setError(e.message);
    }
  }

  async function deleteAccount() {
    if (!window.confirm("Zrušiť účet aj so všetkými meraniami a headsetmi? Nedá sa to vrátiť.")) return;
    try {
      await api.deleteMyAccount();
      onAccountDeleted();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <main className="view">
      <header className="view-head">
        <div>
          <h1>Môj Oculus</h1>
          <p className="muted">Spáruj headset so svojím účtom. Merania z neho sa uložia pod kód {user.participant ?? "tvojho účtu"}, nie pod tvoje meno.</p>
        </div>
      </header>

      {error && <p className="banner" role="alert">{error}</p>}
      {note && <p className="note" role="status">{note}</p>}

      <section className="analysis">
        <h2>Pripojiť Oculus</h2>
        {left ? (
          <div className="pairing">
            <p className="pairing-code num" aria-label={`Párovací kód ${code.value.split("").join(" ")}`}>{spacedCode(code.value)}</p>
            <p>Zadaj tento kód v simulátore. Platí ešte <b className="num">{left}</b> a dá sa použiť raz.</p>
            <button className="quiet" onClick={newCode}>Vygenerovať nový kód</button>
          </div>
        ) : (
          <div className="pairing">
            <p>{code ? "Kód vypršal. Vypýtaj si nový." : "Vypýtaj si kód a zadaj ho v simulátore na Oculuse."}</p>
            <button className="primary" onClick={newCode}>Pripojiť Oculus</button>
          </div>
        )}
      </section>

      <section className="analysis">
        <h2>Spárované headsety</h2>
        {devices.length === 0 ? (
          <p className="empty">Zatiaľ nemáš spárovaný žiadny headset.</p>
        ) : (
          <div className="table-wrap">
            <table className="plain">
              <thead>
                <tr>
                  <th scope="col">Headset</th>
                  <th scope="col">Stav</th>
                  <th scope="col"><span className="sr-only">Akcia</span></th>
                </tr>
              </thead>
              <tbody>
                {devices.map((d) => (
                  <tr key={d.id}>
                    <th scope="row">Spárovaný {new Date(d.paired_at * 1000).toLocaleString("sk-SK", { dateStyle: "medium", timeStyle: "short" })}</th>
                    <td>{deviceStatus(d, now)}</td>
                    <td><button className="link" onClick={() => disconnect(d)}>Odpojiť</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="analysis">
        <h2>Moje údaje</h2>
        <p className="muted">Výskumník vidí tvoje merania len pod kódom, tvoje meno nevidí. Merania aj účet si môžeš kedykoľvek vymazať.</p>
        <div className="actions danger-actions">
          <button className="quiet" onClick={eraseData}>Vymazať moje merania</button>
          <button className="link" onClick={deleteAccount}>Zrušiť účet</button>
        </div>
      </section>
    </main>
  );
}
