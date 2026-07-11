import type { StatusMeta } from "./model";

export function StatusLabel({ status }: { status: StatusMeta }) {
  return (
    <span className="command-status-label" style={{ background: status.bg, borderColor: status.border }}>
      <span style={{ background: status.dot }} />
      <em style={{ color: status.color }}>{status.label}</em>
    </span>
  );
}
