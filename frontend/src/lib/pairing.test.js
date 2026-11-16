import { describe, expect, it } from "vitest";
import { countdown, deviceStatus, spacedCode } from "./pairing.js";

describe("párovanie", () => {
  it("rozdelí kód na dve trojice, aby sa dal ľahko prepísať", () => {
    expect(spacedCode("K7M2QX")).toBe("K7M 2QX");
  });

  it("odpočítava platnosť kódu a po vypršaní vráti null", () => {
    expect(countdown(1600, 1000)).toBe("10:00");
    expect(countdown(1065, 1000)).toBe("1:05");
    expect(countdown(1000, 1000)).toBeNull();
    expect(countdown(900, 1000)).toBeNull();
  });

  it("opíše stav headsetu", () => {
    expect(deviceStatus({ connected: true, last_seen: 990 }, 1000)).toBe("Pripojený, posiela dáta");
    expect(deviceStatus({ connected: false, last_seen: 940 }, 1000)).toBe("Odpojený, naposledy pred 1 min");
    expect(deviceStatus({ connected: false, last_seen: 1000 - 7300 }, 1000)).toBe("Odpojený, naposledy pred 2 h");
    expect(deviceStatus({ connected: false, last_seen: null }, 1000)).toBe("Spárovaný, zatiaľ sa nepripojil");
  });
});

describe("rola člen", () => {
  it("vymazať svoje údaje môže len člen", async () => {
    const { can } = await import("./roles.js");
    expect(["admin", "researcher", "member"].map((r) => can(r, "eraseOwnData"))).toEqual([false, false, true]);
  });
});
