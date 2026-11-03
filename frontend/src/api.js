import { demoApi } from "./demo.js";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const DEMO = import.meta.env.DEV && new URLSearchParams(window.location.search).has("demo");
const KEY = "dip-token";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

let token = null;
let onUnauthorized = () => {};

try {
  token = sessionStorage.getItem(KEY);
} catch {
  // úložisko nemusí byť dostupné
}

export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

export function hasToken() {
  return DEMO || Boolean(token);
}

export function setToken(value) {
  token = value;
  try {
    if (value) sessionStorage.setItem(KEY, value);
    else sessionStorage.removeItem(KEY);
  } catch {
    // ignorované
  }
}

async function request(path, { method = "GET", body, raw = false } = {}) {
  const res = await fetch(BASE + path, {
    method,
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401 && token) onUnauthorized();
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      // odpoveď nie je JSON
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : "Neplatná požiadavka");
  }
  return raw ? res : res.json();
}

const realApi = {
  login: (username, password) => request("/auth/login", { method: "POST", body: { username, password } }),
  me: () => request("/auth/me"),
  sessions: () => request("/sessions"),
  samples: (id, since) =>
    request(`/sessions/${id}/samples?max_points=2500${since != null ? `&since=${since}` : ""}`),
  summary: (id) => request(`/sessions/${id}/summary`),
  risk: (id) => request(`/sessions/${id}/risk`),
  riskHistory: (id) => request(`/sessions/${id}/risk/history`),
  erase: (code) => request(`/participants/${code}`, { method: "DELETE" }),
  async download(id, format) {
    const res = await request(`/sessions/${id}/export?format=${format}`, { raw: true });
    const url = URL.createObjectURL(await res.blob());
    const a = Object.assign(document.createElement("a"), { href: url, download: `${id}.${format}` });
    a.click();
    URL.revokeObjectURL(url);
  },
};

export const api = DEMO ? demoApi : realApi;
