import React from "react";

/**
 * @startingPoint section="Core" subtitle="Text field with label, icon and error state" viewport="700x260"
 */
export interface InputProps {
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  label?: string;
  required?: boolean;
  type?: "text" | "email" | "password" | "tel";
  disabled?: boolean;
  error?: boolean;
  /** Small helper/error line under the field. */
  hint?: string;
  /** Leading icon element, e.g. <Icon name="search" />. */
  icon?: React.ReactNode;
  /** Trailing element, e.g. a show/hide password toggle. */
  suffix?: React.ReactNode;
  fullWidth?: boolean;
}

export function Input(props: InputProps): JSX.Element;
