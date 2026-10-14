import { describe, expect, it } from "vitest";
import { fmtAge, fmtBig, fmtDateTime, fmtMoney, fmtNum, fmtPct } from "./format";

describe("formato español", () => {
  it("agrupa miles con punto y decimales con coma, también con 4 cifras", () => {
    expect(fmtNum(1234.56)).toBe("1.234,56");
    expect(fmtMoney(1234.56, "EUR")).toBe("1.234,56 €");
    expect(fmtMoney(412.5, "USD")).toBe("412,50 $");
  });

  it("usa el signo menos tipográfico y + opcional", () => {
    expect(fmtPct(-0.082)).toBe("−8,2 %");
    expect(fmtPct(0.123, 1, true)).toBe("+12,3 %");
    expect(fmtPct(0)).toBe("0,0 %");
  });

  it("muestra n/d sin dato", () => {
    expect(fmtNum(null)).toBe("n/d");
    expect(fmtPct(Number.NaN)).toBe("n/d");
    expect(fmtMoney(undefined, "EUR")).toBe("n/d");
  });

  it("abrevia cantidades grandes", () => {
    expect(fmtBig(22_091_298_816, "EUR")).toBe("22.091 M€");
    expect(fmtBig(3.2e12, "USD")).toBe("3,2 bill. $");
  });

  it("muestra la hora de Madrid con su zona", () => {
    expect(fmtDateTime("2026-10-14T16:17:00Z")).toBe("14/10/2026 18:17 CEST");
    expect(fmtDateTime("2026-01-14T16:17:00Z")).toBe("14/01/2026 17:17 CET");
  });

  it("describe la antigüedad", () => {
    const now = new Date("2026-10-14T12:00:00Z");
    expect(fmtAge("2026-10-14T11:30:00Z", now)).toBe("hace 30 min");
    expect(fmtAge("2026-10-10T12:00:00Z", now)).toBe("hace 4 días");
  });
});
