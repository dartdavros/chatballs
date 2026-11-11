const overlaySelector = '[role="dialog"], [role="alertdialog"], [aria-modal="true"], dialog[open], .ant-dropdown, .ant-select-dropdown, .ant-popover';
const editingSelector = 'input, textarea, select, [contenteditable], [role="textbox"], [role="combobox"]';

function visible(element: HTMLElement): boolean {
  if (!element.isConnected || element.closest('[hidden], [inert], [aria-hidden="true"]')) return false;
  const style = window.getComputedStyle(element);
  if (style.display === "none" || style.visibility === "hidden" || style.visibility === "collapse") return false;
  return [...element.getClientRects()].some(rect => rect.width > 0 && rect.height > 0
    && rect.bottom > 0 && rect.right > 0 && rect.top < window.innerHeight && rect.left < window.innerWidth);
}

function layer(element: HTMLElement): number {
  let index = 0;
  for (let node: HTMLElement | null = element; node; node = node.parentElement) {
    const value = Number.parseInt(window.getComputedStyle(node).zIndex, 10);
    if (Number.isFinite(value)) index = Math.max(index, value);
  }
  return index;
}

/** Открытое окно без поиска тоже ограничивает shortcut: фон не получает фокус. */
export function searchShortcutTarget(inputs: HTMLInputElement[], target: EventTarget | null): HTMLInputElement | undefined {
  const overlays = [...document.querySelectorAll<HTMLElement>(overlaySelector)].filter(visible);
  const top = overlays.reduce<HTMLElement | undefined>((current, item) => !current || layer(item) >= layer(current) ? item : current, undefined);
  const candidates = inputs.filter(input => !input.matches(":disabled") && !input.readOnly && visible(input)
    && (!top || top.contains(input)));
  const local = target instanceof Element ? target.closest("[data-search-scope]") : null;
  // В раскрытой боковой форме выбирается её поиск. На обычной странице поле
  // одно; последнее зарегистрированное — открытый позже поиск внутри чата.
  return (local ? candidates.filter(input => local.contains(input)).at(-1) : undefined) ?? candidates.at(-1);
}

export function handleSearchShortcut(event: KeyboardEvent, inputs: HTMLInputElement[]): void {
  if (event.defaultPrevented || event.isComposing || event.repeat || event.metaKey || event.ctrlKey || event.altKey) return;
  if (event.target instanceof Element && event.target.closest(editingSelector)) return;
  const matching = inputs.filter(input => input.getAttribute("aria-keyshortcuts") === event.key);
  if (!matching.length) return;
  const field = searchShortcutTarget(matching, event.target);
  if (!field) return;
  event.preventDefault();
  field.focus();
}
