/** A shop dialog and the persistent player form one keyboard focus boundary. */
export function trapModalTab(event: KeyboardEvent, dialog: HTMLElement | null) {
  if (event.key !== 'Tab' || event.ctrlKey || event.metaKey || event.altKey || !dialog || dialog.closest('[inert]')) return;
  const root = dialog.getRootNode() as Document | ShadowRoot;
  const selector = 'button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex="0"]';
  const panel = root.querySelector<HTMLElement>('.case-control-panel');
  const targets = [...dialog.querySelectorAll<HTMLElement>(selector), ...(panel?.querySelectorAll<HTMLElement>(selector) ?? [])]
    .filter(element => element.offsetParent !== null && !element.closest('[inert]'));
  if (!targets.length) return;
  const index = targets.indexOf(root.activeElement as HTMLElement);
  const next = index < 0 ? event.shiftKey ? targets.length - 1 : 0
    : (index + (event.shiftKey ? -1 : 1) + targets.length) % targets.length;
  event.preventDefault();
  targets[next].focus();
}
