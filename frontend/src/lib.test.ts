import { describe, expect, it } from "vitest";
import { format, parseAxis, metric } from "./lib";
describe("measurement presentation", () => {
  it("preserves unavailable metrics and real zero", () => {
    expect(format(null)).toBe("—");
    expect(format(0)).toBe("0");
    expect(metric(undefined, "ipc")).toBeNull();
  });
  it("bounds and validates sweep axes", () => {
    expect(parseAxis("16,32,16")).toEqual([16, 32]);
    for (const value of ["", "0", "16,no", "1,2,3,4,5", "1.5"])
      expect(() => parseAxis(value)).toThrow();
  });
});
