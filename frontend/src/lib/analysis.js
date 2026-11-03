import { formatClock, headSpeed } from "./series.js";

const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);

// Súhrn po fázach: trvanie, priemerný tep, rýchlosť hlavy, odhad strachu a reakčný čas.
// `points` majú phase a t; `risk` sú {t, fear?, arousal?}; `events` {t, phase, kind, value_ms}.
export function analyzePhases(points, risk, events) {
  const speeds = headSpeed(points);
  const phases = [...new Set(points.map((p) => p.phase))].sort((a, b) => a - b);
  const riskKey = risk.some((r) => r.fear != null) ? "fear" : "arousal";
  return phases.map((phase) => {
    const own = points.filter((p) => p.phase === phase);
    const t0 = own[0].t;
    const t1 = own[own.length - 1].t;
    const inPhase = (r) => r.t >= t0 && r.t <= t1;
    return {
      phase,
      durationS: t1 - t0,
      hrMean: mean(own.map((p) => p.hr).filter((v) => v != null)),
      headSpeedMean: mean(speeds.filter(inPhase).map((s) => s.speed)),
      riskMean: mean(risk.filter(inPhase).map((r) => r[riskKey]).filter((v) => v != null)),
      reactionMs: mean(events.filter((e) => e.phase === phase && e.kind === "reaction_time").map((e) => e.value_ms)),
    };
  });
}

export function peak(risk, key) {
  const values = risk.map((r) => r[key]).filter((v) => v != null);
  return values.length ? Math.max(...values) : null;
}

// Podiel okien s odhadom nad prahom (0 až 1).
export function shareAbove(risk, key, threshold = 0.7) {
  const values = risk.map((r) => r[key]).filter((v) => v != null);
  return values.length ? values.filter((v) => v >= threshold).length / values.length : null;
}

// Jedna veta o tom, čo je v relácii najdôležitejšie: vrchol odhadu a zmena tepu oproti prvej fáze.
export function finding(points, risk, phaseName) {
  const key = risk.some((r) => r.fear != null) ? "fear" : "arousal";
  const rows = risk.filter((r) => r[key] != null);
  if (!rows.length) return null;
  const top = rows.reduce((a, b) => (b[key] > a[key] ? b : a));
  const noun = key === "fear" ? "strachu" : "vzrušenia";
  // Slovenský lokál: „vo fáze 2“, nie „vo fáza 2“.
  const loc = (p) => phaseName(p).toLowerCase().replace(/^fáza/, "fáze");
  let text = `Odhad ${noun} vrcholil na ${Math.round(top[key] * 100)} % v čase ${formatClock(top.t)}.`;
  const phases = analyzePhases(points, risk, []);
  if (phases.length > 1 && phases[0].hrMean != null) {
    const delta = Math.round(phases[phases.length - 1].hrMean - phases[0].hrMean);
    const rel = delta === 0 ? "rovnaký ako" : `o ${Math.abs(delta)} bpm ${delta > 0 ? "vyšší" : "nižší"} než`;
    text += ` Tep vo ${loc(phases[phases.length - 1].phase)} je ${rel} v ${loc(phases[0].phase)}.`;
  }
  return text;
}
