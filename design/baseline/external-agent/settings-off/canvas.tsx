import { useLayoutEffect } from 'react';
import { ConfigProvider } from 'antd';
import { buildTheme } from '../../../../packages/ui/src/theme';
import { ACCENT_PRESETS, applyAppearance } from '../../../../apps/internal-ui/src/shared/appearance';
import { SettingsScreen } from './SettingsScreen';
import { language, tx } from './copy';

export function ExternalSettingsCanvas() {
  const params = new URLSearchParams(location.search);
  const width = [320, 390, 1024, 1440].includes(Number(params.get('width'))) ? Number(params.get('width')) : 1440;
  const dark = params.get('theme') === 'dark';
  const accent = ACCENT_PRESETS.some(([value]) => value === params.get('accent')) ? params.get('accent')! : '#0f9b8e';
  useLayoutEffect(() => { applyAppearance(dark ? 'DARK' : 'LIGHT', accent); document.title = tx('title'); }, [dark, accent]);
  function choose(key: string, value: string) {
    const url = new URL(location.href); url.searchParams.set(key, value); location.href = url.href;
  }
  function control(key: 'width' | 'theme' | 'language' | 'accent', value: string, options: string[][]) {
    return <label>{tx(key)}<select value={value} aria-label={tx(key)} onChange={event => choose(key === 'language' ? 'lang' : key, event.target.value)}>
      {options.map(([id, label]) => <option value={id} key={id}>{label}</option>)}</select></label>;
  }
  return <ConfigProvider theme={buildTheme(dark, accent)}>
    <div className="ea-canvas">
      <header className="ea-review"><h1>{tx('frame')}</h1><p>{tx('reviewNote')}</p>
        <div className="ea-review-controls">
          {control('width', String(width), [1440, 1024, 390, 320].map(size => [String(size), `${size} px`]))}
          {control('theme', dark ? 'dark' : 'light', [['light', tx('light')], ['dark', tx('dark')]])}
          {control('language', language, [['ru', 'Русский'], ['en', 'English']])}
          {control('accent', accent, ACCENT_PRESETS)}
        </div><p>{tx('proposal')}</p>
      </header>
      <SettingsScreen width={width} height={980} />
    </div>
  </ConfigProvider>;
}
