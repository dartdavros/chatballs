import { describe, expect, it } from "vitest";

import { parseDocYaml } from "./parseDocYaml";

describe("parseDocYaml", () => {
  it("parses a valid YAML into product + documents", () => {
    const text = `
product: foxray
documents:
  - code: foxray-overview
    title: Обзор продукта
    category: OVERVIEW
    inclusionMode: MANDATORY
    content: |
      Многострочный
      текст
  - code: foxray-faq
    title: FAQ
    category: FAQ
    content: Вопрос?
`;
    const result = parseDocYaml(text);

    expect(result.product).toBe("foxray");
    expect(result.documents).toHaveLength(2);
    expect(result.documents[0]).toEqual({ code: "foxray-overview", title: "Обзор продукта", category: "OVERVIEW", content: "Многострочный\nтекст\n", inclusionMode: "MANDATORY" });
    expect(result.documents[1].inclusionMode).toBeUndefined();
  });

  it("treats absent product as global (null)", () => {
    const text = `
documents:
  - code: global-overview
    title: Обзор
    category: OVERVIEW
    content: текст
`;
    expect(parseDocYaml(text).product).toBeNull();
  });

  it("throws on invalid YAML syntax", () => {
    expect(() => parseDocYaml("product: foxray\n  documents: [unclosed")).toThrow(/YAML/);
  });

  it("throws when documents is missing or empty", () => {
    expect(() => parseDocYaml("product: foxray")).toThrow(/documents/);
    expect(() => parseDocYaml("documents: []")).toThrow(/documents/);
  });

  it("throws when a required field is empty", () => {
    const text = `
documents:
  - code: ""
    title: Обзор
    category: OVERVIEW
    content: текст
`;
    expect(() => parseDocYaml(text)).toThrow(/code/);
  });

  it("throws on an invalid inclusionMode", () => {
    const text = `
documents:
  - code: foxray-overview
    title: Обзор
    category: OVERVIEW
    inclusionMode: MAYBE
    content: текст
`;
    expect(() => parseDocYaml(text)).toThrow(/inclusionMode/);
  });
});
