import { formatClock, headSpeed } from "./series.js";

const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);

const stats = (xs) => (xs.length
  ? { min: Math.min(...xs), mean: mean(xs), max: Math.max(...xs) }
  : { min: null, mean: null, max: null });

// Jeden riadok súhrnu nad vzorkami `own` (fáza alebo celá relácia) a udalosťami `ownEvents`.
function summarise(phase, own, speeds, risk, ownEvents) {
  const t0 = own[0].t;
  const t1 = own[own.length - 1].t;
  const inRange = (r) => r.t >= t0 && r.t <= t1;
  const riskKey = risk.some((r) => r.fear != null) ? "fear" : "arousal";
  const eventValues = (kind) => ownEvents.filter((e) => e.kind === kind).map((e) => e.value_ms);
  const hr = stats(own.map((p) => p.hr).filter((v) => v != null));
  const head = stats(speeds.filter(inRange).map((s) => s.speed));
  const reaction = stats(eventValues("reaction_time"));
  return {
    phase,
    startT: t0,
    endT: t1,
    durationS: t1 - t0,
    hrMin: hr.min,
    hrMean: hr.mean,
    hrMax: hr.max,
    headSpeedMin: head.min,
    headSpeedMean: head.mean,
    headSpeedMax: head.max,
    riskMean: mean(risk.filter(inRange).map((r) => r[riskKey]).filter((v) => v != null)),
    reactionMin: reaction.min,
    reactionMs: reaction.mean,
    reactionMax: reaction.max,
    task1Ms: mean(eventValues("task1_time")),
    task2Ms: mean(eventValues("task2_time")),
  };
}

// Súhrn po fázach: začiatok, koniec, tep, rýchlosť hlavy a reakčný čas (najmenší, priemerný, najväčší),
// odhad strachu a časy úloh. `points` majú phase a t; `risk` sú {t, fear?, arousal?}; `events` {t, phase, kind, value_ms}.
export function analyzePhases(points, risk, events) {
  const speeds = headSpeed(points);
  const phases = [...new Set(points.map((p) => p.phase))].sort((a, b) => a - b);
  return phases.map((phase) => summarise(
    phase, points.filter((p) => p.phase === phase), speeds, risk, events.filter((e) => e.phase === phase),
  ));
}

// Ten istý súhrn za celú reláciu. `phase` je null.
export function analyzeSession(points, risk, events) {
  return points.length ? summarise(null, points, headSpeed(points), risk, events) : null;
}

const CSV_COLUMNS = [
  ["zaciatok_s", "startT"], ["koniec_s", "endT"], ["trvanie_s", "durationS"],
  ["tep_min", "hrMin"], ["tep_priemer", "hrMean"], ["tep_max", "hrMax"],
  ["hlava_min", "headSpeedMin"], ["hlava_priemer", "headSpeedMean"], ["hlava_max", "headSpeedMax"],
  ["strach_priemer", "riskMean"],
  ["reakcia_min_ms", "reactionMin"], ["reakcia_priemer_ms", "reactionMs"], ["reakcia_max_ms", "reactionMax"],
  ["uloha1_ms", "task1Ms"], ["uloha2_ms", "task2Ms"],
];

// Súhrn ako CSV. Riadok s `phase: null` je celá relácia, chýbajúca hodnota je prázdne pole.
export function summaryCsv(rows, phaseName) {
  const cell = (v) => (v == null ? "" : String(Math.round(v * 1000) / 1000));
  const lines = rows.map((r) => [r.phase == null ? "Celá relácia" : phaseName(r.phase), ...CSV_COLUMNS.map(([, key]) => cell(r[key]))].join(","));
  return [["faza", ...CSV_COLUMNS.map(([name]) => name)].join(","), ...lines].join("\n");
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
