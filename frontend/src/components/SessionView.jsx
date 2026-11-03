import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api.js";
import { analyzePhases, finding, peak, shareAbove } from "../lib/analysis.js";
import { appendPoints, formatClock, headSpeed, lastWithin, phaseSegments, valueAt } from "../lib/series.js";
import AnalysisTable from "./AnalysisTable.jsx";
import RiskGauge from "./RiskGauge.jsx";
import { isLive } from "./SessionRail.jsx";
import TimeChart from "./TimeChart.jsx";

// Jediná farba obrazovky patrí odhadu strachu. Ostatné rady sú v atramente, porovnanie je šedé.
const COLORS = { fear: "var(--accent)", arousal: "var(--comparison)", ink: "var(--text)" };
const LIVE_WINDOW_S = 90;
const phaseName = (p) => `Fáza ${p + 1}`;

// Načíta reláciu a v živom režime každú sekundu dotiahne nové vzorky a odhad.
function useSession(session, live) {
  const id = session.id;
  const [points, setPoints] = useState([]);
  const [risk, setRisk] = useState([]);
  const [summary, setSummary] = useState({ events: [], questionnaires: [] });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const lastT = useRef(null);
  const ticks = useRef(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setPoints([]);
    setRisk([]);
    setError("");
    Promise.all([api.samples(id), api.riskHistory(id).catch(() => []), api.summary(id)])
      .then(([pts, hist, sum]) => {
        if (cancelled) return;
        lastT.current = pts.length ? pts[pts.length - 1].t : null;
        setPoints(pts);
        setRisk(hist);
        setSummary(sum);
      })
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    if (!live) return undefined;
    const timer = setInterval(async () => {
      try {
        const fresh = await api.samples(id, lastT.current);
        if (fresh.length) {
          lastT.current = fresh[fresh.length - 1].t;
          setPoints((old) => appendPoints(old, fresh));
          const probabilities = (await api.risk(id).catch(() => null))?.probabilities;
          if (probabilities) setRisk((old) => appendPoints(old, [{ t: lastT.current, ...probabilities }], 3000));
        }
        if (++ticks.current % 5 === 0) setSummary(await api.summary(id));
        setError("");
      } catch (e) {
        setError(`Spojenie s API vypadlo: ${e.message}`);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [id, live]);

  return { points, risk, summary, error, loading };
}

function Stat({ label, value, unit }) {
  return (
    <div className="stat">
      <dt>{label}</dt>
      <dd>{value}{value !== "–" && unit && <small>{unit}</small>}</dd>
    </div>
  );
}

export default function SessionView({ session, user, onErased }) {
  const [live, setLive] = useState(() => Boolean(isLive(session)));
  const [wholeSession, setWholeSession] = useState(false);
  const [hoverT, setHoverT] = useState(null);
  const { points, risk, summary, error, loading } = useSession(session, live);

  useEffect(() => setLive(Boolean(isLive(session))), [session.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const t0 = points[0]?.t ?? 0;
  const rel = useMemo(() => points.map((p) => ({ ...p, t: p.t - t0 })), [points, t0]);
  const relRisk = useMemo(() => risk.map((r) => ({ ...r, t: r.t - t0 })), [risk, t0]);
  const speed = useMemo(() => headSpeed(rel), [rel]);
  const events = useMemo(
    () => (summary.events ?? []).map((e) => ({ ...e, t: e.t - t0 })),
    [summary.events, t0],
  );
  const bands = useMemo(() => phaseSegments(rel), [rel]);
  const analysis = useMemo(() => analyzePhases(rel, relRisk, events), [rel, relRisk, events]);

  const end = rel.length ? rel[rel.length - 1].t : 0;
  const follow = live && !wholeSession;
  const xDomain = [follow ? Math.max(0, end - LIVE_WINDOW_S) : 0, Math.max(end, 1)];
  const view = (rows) => (follow ? lastWithin(rows, LIVE_WINDOW_S) : rows);

  const hasFear = relRisk.some((r) => r.fear != null);
  const mainKey = hasFear ? "fear" : "arousal";
  const peakValue = peak(relRisk, mainKey);
  const share = shareAbove(relRisk, mainKey);
  const sentence = useMemo(() => finding(rel, relRisk, phaseName), [rel, relRisk]);
  const gaugeAt = (key) => (hoverT == null ? relRisk[relRisk.length - 1]?.[key] : valueAt(relRisk, hoverT, key)) ?? null;
  const riskSeries = [
    ...(hasFear ? [{ key: "fear", label: "Strach", color: COLORS.fear }] : []),
    { key: "arousal", label: "Vzrušenie", color: hasFear ? COLORS.arousal : COLORS.fear },
  ];
  const common = { xDomain, bands, hoverT, onHover: setHoverT, showClock: true };
  const marks = events.filter((e) => e.kind === "reaction_time").map((e) => ({ t: e.t, label: `Reakcia ${Math.round(e.value_ms)} ms` }));

  async function erase() {
    if (!window.confirm(`Vymazať účastníka ${session.participant} aj všetky jeho relácie? Nedá sa to vrátiť.`)) return;
    try {
      await api.erase(session.participant);
      onErased();
    } catch (e) {
      window.alert(e.message);
    }
  }

  return (
    <main className="view">
      <header className="view-head">
        <div>
          <h1>{session.participant}</h1>
          <p className="muted">Relácia {session.id}</p>
          {sentence && <p className="finding">{sentence}</p>}
        </div>
        <div className="actions">
          <button className="chip" aria-pressed={live} onClick={() => setLive(!live)}>
            {live ? "Živý prenos" : "Záznam"}
          </button>
          {live && (
            <button className="chip" aria-pressed={wholeSession} onClick={() => setWholeSession(!wholeSession)}>
              {wholeSession ? "Celá relácia" : `Posledných ${LIVE_WINDOW_S} s`}
            </button>
          )}
          <button className="primary" onClick={() => api.download(session.id, "csv")}>Stiahnuť CSV</button>
          <button className="quiet" onClick={() => api.download(session.id, "json")}>Stiahnuť JSON</button>
          {user.role === "admin" && <button className="link" onClick={erase}>Vymazať účastníka</button>}
        </div>
      </header>

      {error && <p className="banner" role="alert">{error}</p>}
      {loading && <p className="muted">Načítavam reláciu</p>}
      {!loading && points.length === 0 && !error && (
        <p className="empty">Relácia zatiaľ nemá žiadne vzorky.</p>
      )}

      {points.length > 0 && (
        <>
          <dl className="stats">
            <Stat label="Trvanie" value={formatClock(end)} />
            <Stat label="Tep teraz" value={rel[rel.length - 1].hr != null ? String(Math.round(rel[rel.length - 1].hr)) : "–"} unit="bpm" />
            <Stat label="Najvyšší odhad" value={peakValue == null ? "–" : String(Math.round(peakValue * 100))} unit="%" />
            <Stat label="Podiel času nad 70 %" value={share == null ? "–" : String(Math.round(share * 100))} unit="%" />
          </dl>

          <div className="workspace">
            <div className="charts">
              <TimeChart
                {...common} title="Odhad stavu" unit="%" series={riskSeries} data={view(relRisk)}
                yDomain={[0, 1]} format={(v) => (v * 100).toFixed(0)} markers={marks} height={210}
              />
              <TimeChart {...common} title="Tep" unit=" bpm" height={130} series={[{ key: "hr", label: "Tep", color: COLORS.ink }]} data={view(rel)} />
              <TimeChart
                {...common} title="Pohľad hore a dole" unit="°" height={120}
                series={[{ key: "pitch", label: "Sklon hlavy", color: COLORS.ink }]} data={view(rel)}
              />
              <TimeChart
                {...common} title="Rýchlosť otáčania hlavy" unit=" °/s" height={110}
                series={[{ key: "speed", label: "Rýchlosť", color: COLORS.ink }]} data={view(speed)}
              />
              <p className="phase-key">
                {bands.map((b, i) => (
                  <span key={`${b.phase}-${b.t0}`}><i className={`swatch band-${i % 2}`} aria-hidden="true" />{phaseName(b.phase)} od {formatClock(b.t0)}</span>
                ))}
              </p>
            </div>
            <RiskGauge fear={hasFear ? gaugeAt("fear") : null} arousal={gaugeAt("arousal")} />
          </div>

          <section className="analysis">
            <h2>Súhrn po fázach</h2>
            <AnalysisTable rows={analysis} phaseName={phaseName} />
          </section>
        </>
      )}
    </main>
  );
}
