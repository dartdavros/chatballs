import type { CommandVm } from "./model";

export function StatusLabel({ vm }: { vm: CommandVm }) {
  return (
    <span className="command-status-label" style={{ background: vm.st.bg, borderColor: vm.st.border }}>
      <span style={{ background: vm.st.dot }} />
      <em style={{ color: vm.st.color }}>{vm.st.label}</em>
    </span>
  );
}
