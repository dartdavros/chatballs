/**
 * @startingPoint section="Cards" subtitle="Single KPI cell for metric grids" viewport="700x120"
 */
export interface MetricCardProps {
  label: string;
  value: string | number;
  /** Color override for the number (e.g. warning/error when it needs attention). */
  valueColor?: string;
  /** Small leading status dot, e.g. AI vs operator split. */
  dotColor?: string;
}

export function MetricCard(props: MetricCardProps): JSX.Element;
