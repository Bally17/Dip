// Vymyslené dáta na ukážku rozhrania bez API. Zapína sa len vo vývoji cez ?demo v adrese.
// Skutočné dáta nahrádzajú toto všetko, nič z toho sa nedostane do produkčného buildu.

const T0 = Math.floor(Date.now() / 1000) - 62;
const HZ = 10;
const SECONDS = 60;

function noise(i) {
  return Math.sin(i * 12.9898) * 0.5 + Math.sin(i * 78.233) * 0.5;
}

const points = Array.from({ length: SECONDS * HZ }, (_, i) => {
  const t = T0 + i / HZ;
  const phase = Math.min(2, Math.floor(i / (20 * HZ)));
  return {
    t,
    phase,
    hr: 72 + phase * 13 + Math.sin(t / 4) * 3 + noise(i) * 2,
    pitch: [0, 12, 33][phase] + Math.sin(t / 3) * 4,
    yaw: Math.sin(t / 2) * [10, 18, 30][phase] + noise(i + 7) * (phase + 1),
  };
});

const risk = Array.from({ length: 22 }, (_, k) => {
  const t = T0 + 5 + k * 2.5;
  const phase = Math.min(2, Math.floor((t - T0) / 20));
  return {
    t,
    fear: Math.min(0.95, 0.05 + phase * 0.22 + (k % 3) * 0.02 + Math.max(0, (t - T0 - 40)) * 0.012),
    arousal: Math.min(0.95, 0.2 + phase * 0.25 + (k % 4) * 0.03),
  };
});

const events = Array.from({ length: 12 }, (_, k) => ({
  t: T0 + 4 + k * 4.5,
  phase: Math.min(2, Math.floor((4 + k * 4.5) / 20)),
  kind: "reaction_time",
  value_ms: 380 + Math.min(2, Math.floor((4 + k * 4.5) / 20)) * 90 + noise(k) * 40,
}));

const iso = (offset) => new Date((T0 + offset) * 1000).toISOString();

export const demoApi = {
  login: async () => ({ access_token: "demo", role: "admin" }),
  me: async () => ({ username: "demo", role: "admin" }),
  sessions: async () => [
    { id: "s_demo_live", participant: "p_a1f3c9d207be4e58", started_at: iso(0), samples: points.length, last_ts: new Date().toISOString() },
    { id: "s_demo_old", participant: "p_7c20be915d3a64f1", started_at: iso(-86400), samples: 4210, last_ts: iso(-86000) },
  ],
  samples: async (_id, since) => (since == null ? points : points.filter((p) => p.t > since)),
  summary: async () => ({ events, questionnaires: [] }),
  risk: async () => ({ probabilities: risk[risk.length - 1] }),
  riskHistory: async () => risk,
  erase: async () => ({}),
  download: async () => {},
};
