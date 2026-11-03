import { describe, expect, it } from "vitest";
import { analyzePhases, peak, shareAbove } from "./analysis.js";
import { appendPoints, formatClock, headSpeed, lastWithin, phaseSegments, valueAt } from "./series.js";

const pt = (t, phase = 0, extra = {}) => ({ t, phase, hr: 80, pitch: 0, yaw: 0, ...extra });

describe("series", () => {
  it("splits points into phase segments", () => {
    const segs = phaseSegments([pt(0, 0), pt(1, 0), pt(2, 1), pt(3, 1), pt(4, 2)]);
    expect(segs).toEqual([
      { phase: 0, t0: 0, t1: 1 },
      { phase: 1, t0: 2, t1: 3 },
      { phase: 2, t0: 4, t1: 4 },
    ]);
  });

  it("computes head speed and handles yaw wrap-around", () => {
    expect(headSpeed([pt(0, 0, { yaw: 179 }), pt(1, 0, { yaw: -179 })])[0].speed).toBeCloseTo(2);
    expect(headSpeed([pt(0), pt(0.5, 0, { pitch: 10 })])[0].speed).toBeCloseTo(20);
  });

  it("ignores duplicate timestamps when appending and respects the cap", () => {
    const merged = appendPoints([pt(1), pt(2)], [pt(2), pt(3), pt(4)], 3);
    expect(merged.map((p) => p.t)).toEqual([2, 3, 4]);
  });

  it("keeps only the last window", () => {
    expect(lastWithin([pt(0), pt(50), pt(100)], 60).map((p) => p.t)).toEqual([50, 100]);
    expect(lastWithin([], 60)).toEqual([]);
  });

  it("formats clock and finds the nearest value", () => {
    expect(formatClock(75)).toBe("1:15");
    expect(formatClock(-3)).toBe("0:00");
    expect(valueAt([{ t: 0, a: 1 }, { t: 10, a: 2 }], 8, "a")).toBe(2);
    expect(valueAt([], 8, "a")).toBeNull();
  });
});

describe("analysis", () => {
  const points = [pt(0, 0, { hr: 70 }), pt(1, 0, { hr: 74 }), pt(2, 1, { hr: 90 }), pt(3, 1, { hr: 100 })];
  const risk = [{ t: 1, fear: 0.2 }, { t: 3, fear: 0.8 }];
  const events = [
    { t: 1, phase: 1, kind: "reaction_time", value_ms: 400 },
    { t: 2, phase: 1, kind: "reaction_time", value_ms: 500 },
  ];

  it("summarises per phase", () => {
    const rows = analyzePhases(points, risk, events);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({ phase: 0, durationS: 1, hrMean: 72, reactionMs: null });
    expect(rows[1]).toMatchObject({ phase: 1, hrMean: 95, reactionMs: 450 });
    expect(rows[1].riskMean).toBeCloseTo(0.8);
  });

  it("falls back to arousal when there is no fear model", () => {
    expect(analyzePhases(points, [{ t: 1, arousal: 0.4 }], [])[0].riskMean).toBeCloseTo(0.4);
  });

  it("handles empty input", () => {
    expect(analyzePhases([], [], [])).toEqual([]);
    expect(peak([], "fear")).toBeNull();
    expect(shareAbove([], "fear")).toBeNull();
  });

  it("computes peak and share above threshold", () => {
    expect(peak(risk, "fear")).toBe(0.8);
    expect(shareAbove(risk, "fear", 0.7)).toBe(0.5);
  });
});
