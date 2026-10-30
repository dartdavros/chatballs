import type { Binding } from "./types";

export function sameReference(a?: Binding, b?: Binding) {
  return Boolean(a && b && a.source === b.source && a.name === b.name && a.step === b.step
    && (a.path ?? "") === (b.path ?? "") && a.aspect === b.aspect);
}
