import { FormField } from "../../shared/form-controls";

export function ProfileField(props: { label: string; value: string; onChange?: (value: string) => void; placeholder?: string; type?: "text" | "password"; mono?: boolean; disabled?: boolean }) {
  return <FormField {...props} />;
}
