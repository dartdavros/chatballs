import { FormField } from '../../../../apps/internal-ui/src/shared/form-controls';

// Same empty-value bullet placeholder as the saved SpeechKit key. No credential is stored.
export function MaskedKeyField({ label, direction }: { label: string; direction: 'incoming' | 'outgoing' }) {
  return <div className="service-field" data-saved-secret={direction}>
    <FormField label={label} type="password" value="" placeholder="••••••••••••" mono disabled />
  </div>;
}
