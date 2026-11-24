/** Immutable server-rendered communication. srcDoc requires an empty iframe sandbox. */
export type MessagePresentation = {
  formatVersion?: 1;
  contentHtml?: string;
  presentation?: {
    formatVersion: 1;
    css: string;
    isolation: "sandboxed-iframe";
    sandbox: "";
    srcDoc: string;
  };
  deliveryRepresentation?: "html" | "text";
  template?: { skillId: string; skillRevision: number; id: string; name: string; documentPath?: string };
};
