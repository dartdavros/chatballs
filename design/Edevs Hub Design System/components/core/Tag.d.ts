import React from "react";

/**
 * @startingPoint section="Core" subtitle="Status pill and rectangular label tag" viewport="700x150"
 */
export interface TagProps {
  children?: React.ReactNode;
  tone?: "neutral" | "primary" | "success" | "warning" | "error" | "ai";
  /** Rounded-full status chip (with dot) vs a small rectangular label tag (products/channels in tables). */
  pill?: boolean;
  dot?: boolean;
  dotColor?: string;
}

export function Tag(props: TagProps): JSX.Element;
