import { useState } from 'react';
import { Icon } from '../../../../../apps/internal-ui/src/shared/icons';
import { Button } from '../../../../../apps/internal-ui/src/shared/ui-controls';
import { FeatureCard } from './FeatureCard';
import { ConnectionCard } from './ConnectionCard';
import { BindingCard } from './BindingCard';
import { ProcessingCard } from './ProcessingCard';
import { DataPolicyCard } from './DataPolicyCard';
import { TemplatePolicyCard } from './TemplatePolicyCard';
import { NewlyCreatedKey, SettingsConfirmation } from './SecurityStates';
import { tx } from './copy';
import { SettingsLoadState } from './SettingsLoadState';
import { SettingsSaveFooter } from './SettingsSaveFooter';
import './state-layout.css';

export function SettingsBody({ variant, width }: { variant: string; width: number }) {
  const [edited, setEdited] = useState(false);
  if (variant === 'S31' || variant === 'S32') return <SettingsLoadState failed={variant === 'S32'} />;
  if (variant === 'S36') return <section className="administration-card" style={{ minHeight: 440 }} data-settings-permission="denied">
    <div className="settings-card-head"><div><strong>{tx('readonly')}</strong></div></div>
    <div className="settings-risk-note" role="alert"><Icon name="lock" size={16} /><p>{tx('readonlyHelp')}</p></div>
  </section>;
  const disabled = ['S34', 'S38', 'S72'].includes(variant), review = variant === 'S39';
  return <>
    <FeatureCard variant={variant} />
    {variant === 'S24' && <NewlyCreatedKey />}
    <ConnectionCard variant={variant} width={width} />
    <BindingCard disabled={disabled} review={review} onDirty={() => setEdited(true)} /><ProcessingCard disabled={disabled} />
    <DataPolicyCard variant={variant} /><TemplatePolicyCard variant={variant} />
    <SettingsSaveFooter variant={variant} edited={edited} />
    {review && <div className="administration-actions"><Button variant="primary" onClick={() => {}}>{tx('configure')}</Button></div>}
    <SettingsConfirmation variant={variant} />
  </>;
}
