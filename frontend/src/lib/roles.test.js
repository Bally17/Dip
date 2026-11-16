import { describe, expect, it } from "vitest";
import { can, roleLabel } from "./roles.js";

describe("roly", () => {
  it("pomenuje rolu po slovensky", () => {
    expect(["admin", "researcher", "member"].map(roleLabel)).toEqual(["admin", "výskumník", "člen"]);
  });

  it("účty spravuje len admin", () => {
    expect(["admin", "researcher", "member"].map((r) => can(r, "manageUsers"))).toEqual([true, false, false]);
  });

  it("cudzie údaje maže len admin, headset si páruje len člen", () => {
    expect(["admin", "researcher", "member"].map((r) => can(r, "eraseParticipant"))).toEqual([true, false, false]);
    expect(["admin", "researcher", "member"].map((r) => can(r, "pairDevice"))).toEqual([false, false, true]);
  });
});
