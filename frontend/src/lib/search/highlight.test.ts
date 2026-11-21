import { parseHighlight } from "./highlight";

describe("parseHighlight", () => {
  it("splits marker-wrapped matches from plain text", () => {
    expect(parseHighlight("All about \u0002algebra\u0003 and \u0002proofs\u0003")).toEqual([
      { text: "All about ", hit: false },
      { text: "algebra", hit: true },
      { text: " and ", hit: false },
      { text: "proofs", hit: true },
    ]);
  });

  it("returns markup untouched as text, never as elements", () => {
    expect(parseHighlight("<img src=x onerror=alert(1)>")).toEqual([
      { text: "<img src=x onerror=alert(1)>", hit: false },
    ]);
  });

  it("handles empty and unbalanced input", () => {
    expect(parseHighlight("")).toEqual([]);
    expect(parseHighlight("open \u0002never closed")).toEqual([
      { text: "open ", hit: false },
      { text: "never closed", hit: true },
    ]);
  });
});
