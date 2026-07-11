import React from "react";

/**
 * @startingPoint section="Cards" subtitle="AI knowledge/prompt release snapshot for one product" viewport="700x180"
 */
export interface ProductAIReleaseCardProps {
  productName: string;
  productInitial: string;
  /** Technical release id, shown in monospace (e.g. "REL-FX-0042"). */
  releaseId: string;
  live?: boolean;
  iconBg?: string;
  iconColor?: string;
  stats?: { label: string; value: string | number }[];
}

export function ProductAIReleaseCard(props: ProductAIReleaseCardProps): JSX.Element;
