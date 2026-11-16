import { formatClock } from "../lib/series.js";

const seconds = (ms) => (ms == null ? "–" : <>{(ms / 1000).toFixed(1)}<small>s</small></>);

// Tri hodnoty jednej veličiny: najmenšia, priemerná (zvýraznená) a najväčšia.
function Range({ min, mean, max, unit }) {
  if (mean == null) return "–";
  return (
    <span className="range">
      {min.toFixed(0)}<i aria-hidden="true">/</i><b>{mean.toFixed(0)}</b><i aria-hidden="true">/</i>{max.toFixed(0)}<small>{unit}</small>
    </span>
  );
}

function Row({ row, label }) {
  return (
    <tr className={row.phase == null ? "total" : undefined}>
      <th scope="row">{label}</th>
      <td>{formatClock(row.startT)}</td>
      <td>{formatClock(row.endT)}</td>
      <td>{formatClock(row.durationS)}</td>
      <td><Range min={row.hrMin} mean={row.hrMean} max={row.hrMax} unit="bpm" /></td>
      <td><Range min={row.headSpeedMin} mean={row.headSpeedMean} max={row.headSpeedMax} unit="°/s" /></td>
      <td>{row.riskMean == null ? "–" : <>{Math.round(row.riskMean * 100)}<small>%</small></>}</td>
      <td><Range min={row.reactionMin} mean={row.reactionMs} max={row.reactionMax} unit="ms" /></td>
      <td>{seconds(row.task1Ms)}</td>
      <td>{seconds(row.task2Ms)}</td>
    </tr>
  );
}

export default function AnalysisTable({ rows, total, phaseName }) {
  if (!rows.length) return <p className="empty">Po prvých vzorkách sa tu zobrazí súhrn po fázach.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col">Fáza</th>
            <th scope="col">Začiatok</th>
            <th scope="col">Koniec</th>
            <th scope="col">Trvanie</th>
            <th scope="col">Tep<small>min / priemer / max</small></th>
            <th scope="col">Rýchlosť hlavy<small>min / priemer / max</small></th>
            <th scope="col">Odhad strachu</th>
            <th scope="col">Reakčný čas<small>min / priemer / max</small></th>
            <th scope="col">Úloha 1</th>
            <th scope="col">Úloha 2</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => <Row key={r.phase} row={r} label={phaseName(r.phase)} />)}
        </tbody>
        {total && (
          <tfoot>
            <Row row={total} label="Celá relácia" />
          </tfoot>
        )}
      </table>
    </div>
  );
}
