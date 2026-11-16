// Riadky panela „Prístroj“ zo stavu prenosu, ktorý počíta server (GET /sessions/{id}/device).

const ago = (seconds) => {
  if (seconds < 60) return `pred ${Math.round(seconds)} s`;
  if (seconds < 3600) return `pred ${Math.floor(seconds / 60)} min`;
  return `pred ${Math.floor(seconds / 3600)} h ${Math.floor((seconds % 3600) / 60)} min`;
};
const comma = (v, digits) => v.toFixed(digits).replace(".", ",");

export function deviceRows(state) {
  if (!state) return [];
  const gaps = state.samples === 0
    ? "–"
    : state.gaps === 0 ? "žiadne" : `${state.gaps}, najdlhší ${comma(state.longest_gap_s, 1)} s`;
  return [
    { label: "Spojenie", value: state.connected ? "Pripojené" : "Bez dát" },
    { label: "Posledná správa", value: state.last_message_age_s == null ? "–" : ago(state.last_message_age_s) },
    { label: "Frekvencia vzoriek", value: state.rate_hz == null ? "–" : `${comma(state.rate_hz, state.rate_hz % 1 ? 1 : 0)} Hz` },
    { label: "Výpadky", value: gaps },
    {
      label: "Oneskorenie",
      value: state.delay_ms == null ? "–" : `${Math.round(state.delay_ms)} ms, najviac ${Math.round(state.delay_max_ms)} ms`,
    },
  ];
}
