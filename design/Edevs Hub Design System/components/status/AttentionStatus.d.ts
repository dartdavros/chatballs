/**
 * @startingPoint section="Status" subtitle="Company/department health chip (ok/attention/critical)" viewport="700x120"
 */
export interface AttentionStatusProps {
  level?: "ok" | "attention" | "critical";
  /** Override the default Russian label for this level. */
  label?: string;
}

export function AttentionStatus(props: AttentionStatusProps): JSX.Element;
