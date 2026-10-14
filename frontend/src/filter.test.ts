import { describe, expect, it } from "vitest";
import { filterResults, modelOptions, sliceRank } from "./lib/types";
import { safeUrl, splitCitations } from "./lib/chat";

describe("filterResults", () => {
  it("ANY returns union", () => {
    const rs = [{ title: "apple pie", snippet: "" }, { title: "banana", snippet: "" }];
    expect(filterResults(rs, ["apple", "banana"], "ANY")).toHaveLength(2);
  });
  it("ALL returns intersection", () => {
    const rs = [{ title: "apple pie", snippet: "" }, { title: "apple banana", snippet: "" }];
    expect(filterResults(rs, ["apple", "banana"], "ALL")).toHaveLength(1);
  });
  it("sliceRank 20-40 gives 21", () => {
    const rs = Array.from({ length: 50 }, (_, i) => ({ title: `t${i}` }));
    expect(sliceRank(rs, 20, 40)).toHaveLength(21);
  });
  it("modelOptions keeps a custom-typed model", () => {
    expect(modelOptions(["a", "b"], "custom/model")).toEqual(["a", "b", "custom/model"]);
    expect(modelOptions(["a", "b"], "a")).toEqual(["a", "b"]);
  });
  it("safeUrl allowlists http(s) only", () => {
    expect(safeUrl("https://example.com/a")).toBe("https://example.com/a");
    expect(safeUrl("http://example.com/")).toBe("http://example.com/");
    expect(safeUrl("javascript:alert(1)")).toBeNull();
    expect(safeUrl("data:text/plain,hi")).toBeNull();
    expect(safeUrl("file:///etc/passwd")).toBeNull();
    expect(safeUrl("not a url")).toBeNull();
  });
  it("splitCitations tokenizes [Sn] markers", () => {
    expect(splitCitations("a [S1] b [S12]")).toEqual([
      { text: "a " }, { cite: 1 }, { text: " b " }, { cite: 12 },
    ]);
    expect(splitCitations("plain")).toEqual([{ text: "plain" }]);
  });
});
