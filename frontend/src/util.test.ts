import { describe, expect, it } from "vitest";
import { pct, todayIndex, weekDates } from "./util";

describe("util", () => {
  it("maps Sunday to 6 and Monday to 0", () => {
    expect(todayIndex(new Date("2026-11-22T12:00:00"))).toBe(6);
    expect(todayIndex(new Date("2026-11-23T12:00:00"))).toBe(0);
  });
  it("week starts on Monday", () => {
    const w = weekDates(new Date("2026-11-25T12:00:00"));
    expect(w[0].getDay()).toBe(1);
    expect(w).toHaveLength(7);
  });
  it("pct is clamped", () => {
    expect(pct(150, 100)).toBe(100);
    expect(pct(5, 0)).toBe(0);
  });
});
