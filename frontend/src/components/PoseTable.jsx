import { formatClock } from "../lib/series.js";

const num = (v, digits, unit) => (v == null ? "–" : <>{v.toFixed(digits)}<small>{unit}</small></>);

// Poloha a orientácia hlavy a oboch ovládačov v jednom okamihu relácie.
export default function PoseTable({ point }) {
  if (!point) return null;
  const rows = [
    { name: "Hlava", pos: point.head_pos, pitch: point.pitch, yaw: point.yaw },
    { name: "Ľavý ovládač", pos: point.left?.pos, pitch: point.left?.pitch, yaw: point.left?.yaw },
    { name: "Pravý ovládač", pos: point.right?.pos, pitch: point.right?.pitch, yaw: point.right?.yaw },
  ];
  return (
    <div className="table-wrap">
      <table className="steady">
        <caption>V čase {formatClock(point.t)}. Poloha je v súradniciach simulátora, os y smeruje nahor.</caption>
        <thead>
          <tr>
            <th scope="col">Čo</th>
            <th scope="col">x</th>
            <th scope="col">y (výška)</th>
            <th scope="col">z</th>
            <th scope="col">Sklon</th>
            <th scope="col">Otočenie</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.name}>
              <th scope="row">{r.name}</th>
              <td>{num(r.pos?.[0], 2, "m")}</td>
              <td>{num(r.pos?.[1], 2, "m")}</td>
              <td>{num(r.pos?.[2], 2, "m")}</td>
              <td>{num(r.pitch, 0, "°")}</td>
              <td>{num(r.yaw, 0, "°")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
