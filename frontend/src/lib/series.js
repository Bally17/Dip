// Pomocné funkcie nad časovými radmi. Čas `t` je v sekundách.

export function phaseSegments(points) {
  const segments = [];
  for (const p of points) {
    const last = segments[segments.length - 1];
    if (last && last.phase === p.phase) last.t1 = p.t;
    else segments.push({ phase: p.phase, t0: p.t, t1: p.t });
  }
  return segments;
}

// Uhlová rýchlosť hlavy v °/s. Yaw sa zalamuje na ±180°.
export function headSpeed(points) {
  const out = [];
  for (let i = 1; i < points.length; i++) {
    const dt = points[i].t - points[i - 1].t;
    if (dt <= 0) continue;
    const dyaw = ((points[i].yaw - points[i - 1].yaw + 540) % 360) - 180;
    const dpitch = points[i].pitch - points[i - 1].pitch;
    out.push({ t: points[i].t, speed: Math.hypot(dyaw, dpitch) / dt });
  }
  return out;
}

// Pridá nové body za existujúce (bez duplicít) a drží najviac `cap` posledných.
export function appendPoints(existing, incoming, cap = 6000) {
  const lastT = existing.length ? existing[existing.length - 1].t : -Infinity;
  const merged = existing.concat(incoming.filter((p) => p.t > lastT));
  return merged.length > cap ? merged.slice(merged.length - cap) : merged;
}

export function lastWithin(points, windowS) {
  if (!points.length || !windowS) return points;
  const end = points[points.length - 1].t;
  return points.filter((p) => p.t >= end - windowS);
}

export function formatClock(seconds) {
  const s = Math.max(0, Math.round(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function valueAt(rows, t, key) {
  if (!rows.length) return null;
  let best = rows[0];
  for (const r of rows) if (Math.abs(r.t - t) < Math.abs(best.t - t)) best = r;
  return best[key] ?? null;
}
