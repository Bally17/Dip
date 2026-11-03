const level = (v) => (v >= 0.7 ? { name: "Vysoký", className: "high" } : v >= 0.4 ? { name: "Zvýšený", className: "" } : { name: "Nízky", className: "" });

function Bar({ label, value, main, ticks }) {
  const known = value != null;
  const lv = known ? level(value) : null;
  return (
    <div className="gauge-col">
      <div className="gauge-bar-wrap">
        <div className="gauge-bar" role="img" aria-label={`${label}: ${known ? Math.round(value * 100) + " %" : "bez údajov"}`}>
          {known && <span className={`gauge-fill ${main ? "is-main" : ""}`} style={{ height: `${Math.max(1, value * 100)}%` }} />}
        </div>
        {ticks && [0.7, 0.4].map((t) => (
          <span key={t} className="gauge-tick num" style={{ bottom: `calc(${t * 100}% - 1px)` }}>{Math.round(t * 100)}</span>
        ))}
      </div>
      <div className="gauge-value">{known ? Math.round(value * 100) : "–"}{known && <small>%</small>}</div>
      <div className="gauge-label">{label}</div>
      <div className={`gauge-level ${lv?.className ?? ""}`}>{lv?.name ?? "Bez údajov"}</div>
    </div>
  );
}

// Zvislý výškomer: čím vyššie, tým väčší odhad. Značky na 40 % a 70 % sú orientačné prahy.
// Hlavný údaj (strach) má jedinú farbu obrazovky, vzrušenie je v atramente.
export default function RiskGauge({ fear, arousal }) {
  return (
    <section className="gauge" aria-label="Aktuálny odhad">
      <h2>Teraz</h2>
      <div className="gauge-cols">
        {fear !== null && <Bar label="Strach" value={fear} main ticks />}
        <Bar label="Vzrušenie" value={arousal} main={fear === null} ticks={fear === null} />
      </div>
      <p className="note">
        Odhad z posledných 5 s tepu a pohybu hlavy. Model je natrénovaný na 360° videách, nie na simulátore, takže
        hodnoty slúžia len orientačne.
      </p>
    </section>
  );
}
