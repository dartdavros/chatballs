export interface CheckboxProps {
  checked?: boolean;
  onChange?: () => void;
  label?: string | JSX.Element;
  size?: "sm" | "md";
}

export function Checkbox(props: CheckboxProps): JSX.Element;
