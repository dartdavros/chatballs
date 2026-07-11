import React from "react";

/**
 * @startingPoint section="Cards" subtitle="Command Center department summary card" viewport="900x360"
 */
export interface DepartmentCardProps {
  name: string;
  meta: string;
  level?: "ok" | "attention" | "critical";
  summary?: string;
  icon?: string;
  openLabel?: string;
  onOpen?: () => void;
  /** MetricCard grids or other detail rows rendered below the summary. */
  children?: React.ReactNode;
}

export function DepartmentCard(props: DepartmentCardProps): JSX.Element;
