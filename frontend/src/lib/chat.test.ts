import { describe, expect, it } from "vitest";
import { safeUrl, splitCitations } from "./chat";

describe("splitCitations", () => {
  it("splits single and multi markers into inline badges", () => {
    const parts = splitCitations("a [S1] b [S1, S3] c");
    expect(parts).toEqual([
      { text: "a " },
      { cite: 1 },
      { text: " b " },
      { cite: 1 },
      { text: ", " },
      { cite: 3 },
      { text: " c" },
    ]);
  });
});

describe("safeUrl", () => {
  it("allows http(s) only", () => {
    expect(safeUrl("https://example.com/a")).toBe("https://example.com/a");
    expect(safeUrl("http://example.com")).toBe("http://example.com");
    expect(safeUrl("javascript:alert(1)")).toBeNull();
    expect(safeUrl("data:text/html,<h1>x</h1>")).toBeNull();
    expect(safeUrl("file:///etc/passwd")).toBeNull();
    expect(safeUrl("not a url")).toBeNull();
  });
});
