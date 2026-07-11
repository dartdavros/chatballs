export interface IconProps {
  /** Which glyph to render — see ICON_NAMES for the full curated set copied from the baseline. */
  name:
    | "dashboard" | "departments" | "employees" | "products" | "ai" | "integrations" | "settings"
    | "search" | "chevronDown" | "chevronRight" | "moreVertical" | "check" | "checkCircle"
    | "alertTriangle" | "alertCircle" | "xCircle" | "clock" | "refresh" | "arrowRight" | "arrowLeft"
    | "mail" | "lock" | "eye" | "eyeOff" | "card" | "sbp" | "shield" | "download" | "columns"
    | "bell" | "trash" | "edit" | "merge" | "bolt" | "cart" | "history" | "team" | "package2";
  /** Pixel size (square). Default 17. */
  size?: number;
  /** Stroke color. Default currentColor. */
  color?: string;
  strokeWidth?: number;
}

export function Icon(props: IconProps): JSX.Element | null;
