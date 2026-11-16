import { createElement, useState } from 'react';
import { CircleHelp } from 'lucide';
import { Modal } from 'antd';
import { Button } from '../../../../../apps/internal-ui/src/shared/ui-controls';
import '../../../../../apps/internal-ui/src/features/agents/styles.css';
import { helpTopics, ht, type HelpTopic } from './help-copy';
import { TemplatePreview } from './TemplatePreview';
import './help.css';

export function HelpTrigger({ topic }: { topic: HelpTopic }) {
  const [open, setOpen] = useState(false);
  const [title, text] = helpTopics[topic];
  return <><button type="button" className="ui-icon-button is-bare external-help-trigger" data-help-topic={topic}
    aria-label={`${ht('about')}${ht(title)}`} title={`${ht('about')}${ht(title)}`} aria-haspopup="dialog" onClick={() => setOpen(true)}>
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {CircleHelp.map(([tag, attrs], index) => createElement(tag, { ...attrs, key: index }))}</svg>
  </button><Modal className="agent-create-modal external-help-modal" open={open} width={440} centered
    title={ht(title)} onCancel={() => setOpen(false)} footer={null} destroyOnHidden>
    <p className="agent-create-lead">{ht(text)}</p>
    {topic === 'templates' && <div className="external-help-example"><small>{ht('example')}</small><TemplatePreview /></div>}
    <div className="agent-create-actions"><Button variant="secondary" onClick={() => setOpen(false)}>{ht('close')}</Button></div>
  </Modal></>;
}
