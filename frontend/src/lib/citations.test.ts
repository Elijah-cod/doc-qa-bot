import { describe, expect, it } from "vitest";
import { answerForClipboard, parseAnswer } from "./citations";

const valid = new Set([1, 2, 3]);

describe("parseAnswer", () => {
  it("splits text and citations", () => {
    expect(parseAnswer("Cats purr [1].", valid)).toEqual([
      { type: "text", text: "Cats purr " },
      { type: "cite", n: 1 },
      { type: "text", text: "." },
    ]);
  });

  it("handles adjacent citations", () => {
    expect(parseAnswer("A [1][3]", valid)).toEqual([
      { type: "text", text: "A " },
      { type: "cite", n: 1 },
      { type: "cite", n: 3 },
    ]);
  });

  it("keeps invalid numbers as plain text", () => {
    expect(parseAnswer("See [9] and [2]", valid)).toEqual([
      { type: "text", text: "See [9] and " },
      { type: "cite", n: 2 },
    ]);
  });

  it("returns one text segment when there are no citations", () => {
    expect(parseAnswer("I couldn't find that in the document.", valid)).toEqual([
      { type: "text", text: "I couldn't find that in the document." },
    ]);
  });

  it("handles empty input", () => {
    expect(parseAnswer("", valid)).toEqual([]);
  });
});

describe("answerForClipboard", () => {
  it("removes invented citation numbers", () => {
    expect(answerForClipboard("A [1] B [7]", valid)).toBe("A [1] B");
  });
});
