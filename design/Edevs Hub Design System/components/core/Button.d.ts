import React from "react";

/**
 * @startingPoint section="Core" subtitle="Primary/secondary/ghost/danger button" viewport="700x220"
 */
export interface ButtonProps {
  children?: React.ReactNode;
  /** Visual treatment. primary = solid blue CTA (one per context per ADR-HUB-0013); secondary = outlined; ghost = borderless; danger = destructive red. */
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  onClick?: (e: React.MouseEvent) => void;
  type?: "button" | "submit";
}

export function Button(props: ButtonProps): JSX.Element;
