const LEVELS = [
  { from: 0.7, name: "Vysoký", className: "high" },
  { from: 0.4, name: "Zvýšený", className: "mid" },
  { from: 0, name: "Nízky", className: "low" },
];

const level = (v) => LEVELS.find((l) => v >= l.from);

function Bar({ label, value }) {
  const known = value != null;
  const lv = known ? level(value) : null;
  return (
    <div className="gauge-col">
      <div className="gauge-bar" role="img" aria-label={`${label}: ${known ? Math.round(value * 100) + " %" : "bez údajov"}`}>
        {[0.7, 0.4].map((t) => (
          <span key={t} className="gauge-tick" style={{ bottom: `${t * 100}%` }}>{Math.round(t * 100)}</span>
        ))}
        {known && <span className={`gauge-fill ${lv.className}`} style={{ height: `${Math.max(2, value * 100)}%` }} />}
      </div>
      <div className="gauge-value">{known ? Math.round(value * 100) : "–"}<small>{known ? " %" : ""}</small></div>
      <div className="gauge-label">{label}</div>
      <div className={`gauge-level ${lv?.className ?? ""}`}>{lv?.name ?? "Bez údajov"}</div>
    </div>
  );
}

// Zvislý výškomer: čím vyššie, tým väčší odhad. Značky na 40 % a 70 % sú orientačné prahy.
export default function RiskGauge({ fear, arousal }) {
  return (
    <section className="gauge" aria-label="Aktuálny odhad">
      <div className="gauge-cols">
        <Bar label="Strach" value={fear} />
        <Bar label="Vzrušenie" value={arousal} />
      </div>
      <p className="note">
        Odhad z posledných 5 s tepu a pohybu hlavy. Model je natrénovaný na 360° videách, nie na simulátore, takže
        hodnoty slúžia len orientačne.
      </p>
    </section>
  );
}
