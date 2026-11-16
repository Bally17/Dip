import { deviceRows } from "../lib/device.js";

// Stav prenosu z prístroja, ako ho vidí server. Údaje zo samotného simulátora (batéria, FPS) tu zatiaľ nie sú.
export default function DevicePanel({ state }) {
  const rows = deviceRows(state);
  if (!rows.length) return <p className="empty">Stav prístroja sa nepodarilo načítať.</p>;
  return (
    <>
      <dl className="device">
        {rows.map((r) => (
          <div key={r.label}>
            <dt>{r.label}</dt>
            <dd className={r.label === "Spojenie" && !state.connected ? "off" : undefined}>{r.value}</dd>
          </div>
        ))}
      </dl>
      <p className="note">
        Hodnoty meria server z času vzorky a času jej prijatia. Oneskorenie je presné, len ak majú prístroj a server zosynchronizované hodiny.
      </p>
    </>
  );
}
