import { formatClock } from "../lib/series.js";

const fmt = (v, unit) => (v == null ? "–" : <>{v.toFixed(0)}<small>{unit}</small></>);

export default function AnalysisTable({ rows, phaseName }) {
  if (!rows.length) return <p className="empty">Po prvých vzorkách sa tu zobrazí súhrn po fázach.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col">Fáza</th>
            <th scope="col">Trvanie</th>
            <th scope="col">Tep (priemer)</th>
            <th scope="col">Rýchlosť hlavy</th>
            <th scope="col">Odhad strachu</th>
            <th scope="col">Reakčný čas</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.phase}>
              <th scope="row">{phaseName(r.phase)}</th>
              <td>{formatClock(r.durationS)}</td>
              <td>{fmt(r.hrMean, "bpm")}</td>
              <td>{fmt(r.headSpeedMean, "°/s")}</td>
              <td>{r.riskMean == null ? "–" : <>{Math.round(r.riskMean * 100)}<small>%</small></>}</td>
              <td>{fmt(r.reactionMs, "ms")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
