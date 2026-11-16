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
    head_pos: [Math.sin(t) * 0.05, 1.7, Math.cos(t) * 0.05],
    left: { pos: [-0.3 + Math.sin(t * 1.3) * 0.04 * (phase + 1), 1.1, 0.2], pitch: 10, yaw: -15 },
    right: { pos: [0.3 + Math.sin(t * 1.7) * 0.05 * (phase + 1), 1.1, 0.2], pitch: 12, yaw: 14 },
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

events.push(
  { t: T0 + 39, phase: 1, kind: "task1_time", value_ms: 14200 },
  { t: T0 + 59, phase: 2, kind: "task2_time", value_ms: 16800 },
);

const iso = (offset) => new Date((T0 + offset) * 1000).toISOString();

// Rola v ukážke: ?demo je admin, ?demo=member je člen.
const demoRole = new URLSearchParams(globalThis.location?.search ?? "").get("demo") === "member" ? "member" : "admin";
const ME = "p_a1f3c9d207be4e58";
const demoDevices = [{ id: "d1", paired_at: T0 - 3600, last_seen: T0 + 60, connected: true }];

const demoUsers = [
  { id: "demo", name: "demo", role: "admin" },
  { id: "p_a1f3c9d207be4e58", name: "p_a1f3c9d207be4e58", role: "member" },
  { id: "p_7c20be915d3a64f1", name: "p_7c20be915d3a64f1", role: "member" },
];

const demoSessions = () => [
  { id: "s_demo_live", participant: "p_a1f3c9d207be4e58", started_at: iso(0), samples: points.length, last_ts: new Date().toISOString() },
  { id: "s_demo_old", participant: "p_7c20be915d3a64f1", started_at: iso(-86400), samples: 4210, last_ts: iso(-86000) },
];

export const demoApi = {
  login: async () => ({ access_token: "demo", role: demoRole }),
  me: async () => ({ username: "demo", role: demoRole, participant: demoRole === "member" ? ME : null }),
  pairingCode: async () => ({ code: "K7M2QX", expires_in_s: 600 }),
  devices: async () => [...demoDevices],
  disconnectDevice: async (id) => {
    demoDevices.splice(demoDevices.findIndex((d) => d.id === id), 1);
    return { deleted: id };
  },
  eraseMyData: async () => ({ erased: true }),
  deleteMyAccount: async () => ({ deleted: true }),
  sessions: async () => demoSessions().filter((s) => demoRole !== "member" || s.participant === ME),
  samples: async (_id, since) => (since == null ? points : points.filter((p) => p.t > since)),
  summary: async () => ({ events }),
  device: async () => ({
    samples: points.length, rate_hz: 10, gaps: 1, longest_gap_s: 1.2, delay_ms: 18, delay_max_ms: 240,
    last_message_age_s: 0.4, connected: true,
  }),
  risk: async () => ({ probabilities: risk[risk.length - 1] }),
  riskHistory: async () => risk,
  erase: async () => ({}),
  users: async () => [...demoUsers],
  createUser: async (_username, _password, role) => {
    const id = `p_${Math.random().toString(16).slice(2, 18)}`;
    const made = { id, name: id, role };
    demoUsers.push(made);
    return made;
  },
  deleteUser: async (id) => {
    demoUsers.splice(demoUsers.findIndex((u) => u.id === id), 1);
    return { deleted: id };
  },
  download: async () => {},
};
