import { describe, expect, it } from "vitest";
import { deviceRows } from "./device.js";

const state = {
  samples: 250, rate_hz: 25, gaps: 2, longest_gap_s: 2.04, delay_ms: 20.4, delay_max_ms: 1500,
  last_message_age_s: 1.2, connected: true,
};
const byLabel = (rows) => Object.fromEntries(rows.map((r) => [r.label, r.value]));

describe("deviceRows", () => {
  it("opíše živé spojenie", () => {
    expect(byLabel(deviceRows(state))).toEqual({
      Spojenie: "Pripojené",
      "Posledná správa": "pred 1 s",
      "Frekvencia vzoriek": "25 Hz",
      Výpadky: "2, najdlhší 2,0 s",
      Oneskorenie: "20 ms, najviac 1500 ms",
    });
  });

  it("opíše prerušené spojenie a prenos bez výpadkov", () => {
    const rows = byLabel(deviceRows({ ...state, connected: false, last_message_age_s: 3725, gaps: 0, longest_gap_s: null }));
    expect(rows.Spojenie).toBe("Bez dát");
    expect(rows["Posledná správa"]).toBe("pred 1 h 2 min");
    expect(rows.Výpadky).toBe("žiadne");
  });

  it("chýbajúce hodnoty ukáže pomlčkou", () => {
    const rows = byLabel(deviceRows({ samples: 0, rate_hz: null, gaps: 0, longest_gap_s: null, delay_ms: null, delay_max_ms: null, last_message_age_s: null, connected: false }));
    expect(rows).toEqual({ Spojenie: "Bez dát", "Posledná správa": "–", "Frekvencia vzoriek": "–", Výpadky: "–", Oneskorenie: "–" });
    expect(deviceRows(null)).toEqual([]);
  });
});
