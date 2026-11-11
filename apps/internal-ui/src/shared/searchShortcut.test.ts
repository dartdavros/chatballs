import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { handleSearchShortcut, searchShortcutTarget } from "./searchShortcut";

// Узкий DOM-double: проверяем арбитраж полей и событий без браузера/API.
// Геометрия задаётся явно, чтобы проверить скрытую мобильную колонку и overlay.
class Node {
  parentElement: Node | null = null;
  isConnected = true;
  readOnly = false;
  disabled = false;
  style = { display: "block", visibility: "visible", zIndex: "auto" };
  rect = { top: 10, right: 210, bottom: 44, left: 10, width: 200, height: 34 };
  focus = vi.fn();
  constructor(public tag: string, public attributes: Record<string, string> = {}) {}
  getAttribute(key: string) { return this.attributes[key] ?? null; }
  getClientRects() { return this.style.display === "none" ? [] : [this.rect]; }
  contains(other: Node): boolean {
    return this === other || Boolean(other.parentElement && this.contains(other.parentElement));
  }
  matches(selector: string): boolean {
    return selector.split(",").some(part => {
      const text = part.trim();
      if (text === ":disabled") return this.disabled;
      if (text.startsWith(".")) return this.attributes.class?.split(" ").includes(text.slice(1));
      const attribute = text.match(/^(\w+)?\[([^=\]]+)(?:="([^"]+)")?\]$/);
      if (attribute) return (!attribute[1] || this.tag === attribute[1]) && attribute[2] in this.attributes
        && (attribute[3] === undefined || this.attributes[attribute[2]] === attribute[3]);
      return this.tag === text;
    });
  }
  closest(selector: string): Node | null {
    return this.matches(selector) ? this : this.parentElement?.closest(selector) ?? null;
  }
}

let nodes: Node[];
function node(tag: string, attributes: Record<string, string> = {}, parent?: Node) {
  const item = new Node(tag, attributes);
  item.parentElement = parent ?? null;
  nodes.push(item);
  return item;
}
function input(parent?: Node) { return node("input", { "aria-keyshortcuts": "/" }, parent); }
function fields(...items: Node[]) { return items as unknown as HTMLInputElement[]; }
function key(target: Node | null = null, overrides: Partial<KeyboardEvent> = {}) {
  return { key: "/", target, preventDefault: vi.fn(), ...overrides } as unknown as KeyboardEvent;
}

beforeEach(() => {
  nodes = [];
  vi.stubGlobal("Element", Node);
  vi.stubGlobal("window", { innerHeight: 800, innerWidth: 1200, getComputedStyle: (item: Node) => item.style });
  vi.stubGlobal("document", { querySelectorAll: (selector: string) => nodes.filter(item => item.matches(selector)) });
});
afterEach(() => { vi.unstubAllGlobals(); });

describe("search shortcut focus", () => {
  it("focuses a search once and consumes only its shortcut", () => {
    const field = input();
    const slash = key();
    handleSearchShortcut(slash, fields(field));
    expect(field.focus).toHaveBeenCalledOnce();
    expect(slash.preventDefault).toHaveBeenCalledOnce();
    const other = key(null, { key: "x" });
    handleSearchShortcut(other, fields(field));
    expect(other.preventDefault).not.toHaveBeenCalled();
    expect(field.focus).toHaveBeenCalledOnce();
  });

  it("keeps focus inside the visible modal instead of the background search", () => {
    const background = input();
    const dialog = node("section", { role: "dialog" });
    const modalSearch = input(dialog);
    expect(searchShortcutTarget(fields(background, modalSearch), null)).toBe(modalSearch);
    dialog.style.display = "none";
    modalSearch.rect.width = 0;
    expect(searchShortcutTarget(fields(background, modalSearch), null)).toBe(background);
  });

  it("does not send focus behind a modal without a search", () => {
    const background = input();
    node("section", { role: "dialog" });
    const slash = key();
    handleSearchShortcut(slash, fields(background));
    expect(background.focus).not.toHaveBeenCalled();
    expect(slash.preventDefault).not.toHaveBeenCalled();
  });

  it("prioritizes the top popup, including its ancestor stacking layer", () => {
    const popup = node("div", { class: "ant-dropdown" });
    popup.style.zIndex = "1050";
    const popupSearch = input(popup);
    const wrap = node("div");
    wrap.style.zIndex = "1000";
    const dialog = node("section", { role: "dialog" }, wrap);
    const modalSearch = input(dialog);
    expect(searchShortcutTarget(fields(popupSearch, modalSearch), null)).toBe(popupSearch);
    wrap.style.zIndex = "1100";
    expect(searchShortcutTarget(fields(popupSearch, modalSearch), null)).toBe(modalSearch);
  });

  it("blocks the background shortcut while a menu without search is open", () => {
    const background = input();
    const menu = node("div", { class: "ant-dropdown" });
    expect(searchShortcutTarget(fields(background), null)).toBeUndefined();
    menu.style.display = "none";
    expect(searchShortcutTarget(fields(background), null)).toBe(background);
  });

  it("prefers the active search region when a second inline picker is open", () => {
    const list = node("section", { "data-search-scope": "" });
    const listSearch = input(list);
    const listButton = node("button", {}, list);
    const side = node("section", { "data-search-scope": "" });
    const sideSearch = input(side);
    expect(searchShortcutTarget(fields(listSearch, sideSearch), listButton as unknown as EventTarget)).toBe(listSearch);
    expect(searchShortcutTarget(fields(listSearch, sideSearch), null)).toBe(sideSearch);
  });

  it.each(["disabled", "readonly", "hidden", "disconnected", "offscreen", "inert"])("ignores %s inputs", condition => {
    const usable = input();
    const unavailable = input();
    if (condition === "disabled") unavailable.disabled = true;
    if (condition === "readonly") unavailable.readOnly = true;
    if (condition === "hidden") unavailable.style.visibility = "hidden";
    if (condition === "disconnected") unavailable.isConnected = false;
    if (condition === "offscreen") unavailable.rect.left = 1500;
    if (condition === "inert") unavailable.parentElement = node("section", { inert: "" });
    expect(searchShortcutTarget(fields(usable, unavailable), null)).toBe(usable);
  });
});

describe("search shortcut typing guards", () => {
  it.each(["input", "textarea", "select", "contenteditable", "textbox", "combobox"])("leaves typing in %s alone", kind => {
    const attributes: Record<string, string> = kind === "contenteditable" ? { contenteditable: "true" }
      : kind === "textbox" || kind === "combobox" ? { role: kind } : {};
    const editing = node(["input", "textarea", "select"].includes(kind) ? kind : "div", attributes);
    const target = node("span", {}, editing);
    const search = input();
    const slash = key(target);
    handleSearchShortcut(slash, fields(search));
    expect(search.focus).not.toHaveBeenCalled();
    expect(slash.preventDefault).not.toHaveBeenCalled();
  });

  it.each(["ctrlKey", "metaKey", "altKey", "isComposing", "repeat", "defaultPrevented"] as const)("respects %s", flag => {
    const field = input();
    const slash = key(null, { [flag]: true });
    handleSearchShortcut(slash, fields(field));
    expect(field.focus).not.toHaveBeenCalled();
    expect(slash.preventDefault).not.toHaveBeenCalled();
  });
});
