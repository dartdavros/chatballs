export class DraftAttempt {
  private generation = 0;
  private applied = false;

  begin(): number { this.applied = false; return ++this.generation; }
  cancel() { ++this.generation; this.applied = false; }
  current(id: number) { return id === this.generation; }
  accept(id: number, text: string, append: (text: string) => void): boolean {
    if (!this.current(id) || this.applied || !text.trim()) return false;
    this.applied = true;
    append(text.trim());
    return true;
  }
}

export const appendDictation = (draft: string, text: string) => `${draft}${draft && !/\s$/.test(draft) ? " " : ""}${text}`;
