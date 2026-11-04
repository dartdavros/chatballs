import * as React from 'react';
import { ArrowUp, Mic, Paperclip, Pause, Play, RotateCcw, Square, Volume2, X, type IconNode } from 'lucide';

const nodes: Record<string, IconNode> = {
  sound: Volume2, stop: Square, play: Play, pause: Pause, refresh: RotateCcw,
  arrow: ArrowUp, mic: Mic, paperclip: Paperclip, close: X,
};
export function SpeechIcon({ name, size = 17 }: { name: string; size?: number }) {
  return <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width={size} height={size}
    fill={name === 'stop' ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
    aria-hidden="true" data-lucide={name}>
    {nodes[name].map(([tag, attributes], index) => React.createElement(tag, { ...attributes, key: index }))}
  </svg>;
}
