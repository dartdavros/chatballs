import React from "react";

/**
 * @startingPoint section="Core" subtitle="Square icon-only button with optional badge" viewport="700x150"
 */
export interface IconButtonProps {
  children?: React.ReactNode;
  size?: number;
  /** Small numeric/text badge in the top-right corner (e.g. notification count). */
  badge?: string | number;
  /** Borderless variant (used inline in tables/menus). */
  bare?: boolean;
  label?: string;
  onClick?: (e: React.MouseEvent) => void;
}

export function IconButton(props: IconButtonProps): JSX.Element;
