import { describe, expect, it } from "vitest";
import { appendLinkifiedText, parseGlossaryHash } from "./glossaryLinkify";
import { setTaGlossaryEntries } from "./taGlossary";

describe("glossaryLinkify", () => {
  it("parses glossary hash anchors", () => {
    expect(parseGlossaryHash("#glossary-CDLDOJI")).toBe("CDLDOJI");
    expect(parseGlossaryHash("")).toBeNull();
  });

  it("renders inline [[ID|label]] links", () => {
    setTaGlossaryEntries([
      {
        id: "CDLDOJI",
        title: "Doji",
        category: "Pattern Recognition",
        short: "indecision",
        long: "long",
        formula: "f",
      },
      {
        id: "CDLABANDONEDBABY",
        title: "Abandoned Baby",
        category: "Pattern Recognition",
        related: ["CDLDOJI"],
        short: "a [[CDLDOJI|doji]] gapped away",
        long: "long",
        formula: "f",
      },
    ]);
    const host = document.createElement("p");
    const clicked: string[] = [];
    appendLinkifiedText(host, "a [[CDLDOJI|doji]] gapped away", (id) => clicked.push(id));
    const link = host.querySelector("a.gp-ta-glossary-link");
    expect(link?.textContent).toBe("doji");
    expect(link?.getAttribute("href")).toBe("#glossary-CDLDOJI");
    link?.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    expect(clicked).toEqual(["CDLDOJI"]);
  });
});
