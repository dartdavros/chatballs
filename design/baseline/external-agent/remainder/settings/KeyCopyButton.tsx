import { useEffect, useRef, useState } from 'react';
import { t } from '../../../../../apps/internal-ui/src/i18n';
import { Icon } from '../../../../../apps/internal-ui/src/shared/icons';
import { tx } from './copy';
import './key-actions.css';

type CopyState = 'idle' | 'copying' | 'copied' | 'error';

// Only the invalid design example is eligible for this local clipboard interaction.
export function KeyCopyButton() {
  const [state, setState] = useState<CopyState>('idle');
  const timer = useRef<ReturnType<typeof window.setTimeout> | null>(null);
  const mounted = useRef(true), busy = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; if (timer.current !== null) window.clearTimeout(timer.current); };
  }, []);

  async function copy() {
    if (busy.current) return;
    busy.current = true;
    if (timer.current !== null) { window.clearTimeout(timer.current); timer.current = null; }
    setState('copying');
    try {
      if (!navigator.clipboard?.writeText) { setState('error'); return; }
      await navigator.clipboard.writeText(tx('keyExample'));
      if (!mounted.current) return;
      setState('copied');
      timer.current = window.setTimeout(() => {
        timer.current = null;
        if (mounted.current) setState('idle');
      }, 3000);
    } catch {
      if (mounted.current) setState('error');
    } finally { busy.current = false; }
  }

  const label = state === 'copied' ? t('common.copied') : state === 'copying' || state === 'error'
    ? tx(state === 'copying' ? 'copyingKey' : 'copyKeyError') : t('common.copy_clipboard');
  return <button type="button" className={`ui-icon-button is-bare ea-key-copy${state === 'copied' ? ' is-copied' : ''}`}
    data-copy-state={state} aria-label={label} title={label} aria-busy={state === 'copying'} disabled={state === 'copying'}
    onClick={event => { event.stopPropagation(); void copy(); }}>
    <Icon name={state === 'copied' ? 'check' : 'copy'} size={18} strokeWidth={1.8} />
  </button>;
}
