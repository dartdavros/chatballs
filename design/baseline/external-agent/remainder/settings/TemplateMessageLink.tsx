import { useState } from 'react';
import { Modal } from 'antd';
import { Button } from '../../../../../apps/internal-ui/src/shared/ui-controls';
import { ht } from '../shared/help-copy';
import { TemplatePreview } from '../shared/TemplatePreview';

// The actual skill editor has no template deep-link. Open the selected design message directly.
export function TemplateMessageLink({ template }: { template: 'greeting' | 'order' }) {
  const [open, setOpen] = useState(false);
  return <><button type="button" className="link" data-open-message={template} aria-label={`${ht('openMessage')}: ${ht(template === 'order' ? 'orderTitle' : 'greetingTitle')}`} onClick={() => setOpen(true)}>{ht('openMessage')}</button>
    <Modal className="agent-create-modal external-help-modal" open={open} width={440} centered
      title={ht(template === 'order' ? 'orderTitle' : 'greetingTitle')} onCancel={() => setOpen(false)} footer={null} destroyOnHidden>
      <div className="external-help-example"><small>{ht('example')}</small><TemplatePreview template={template} /></div>
      <div className="agent-create-actions"><Button variant="secondary" onClick={() => setOpen(false)}>{ht('close')}</Button></div>
    </Modal></>;
}
