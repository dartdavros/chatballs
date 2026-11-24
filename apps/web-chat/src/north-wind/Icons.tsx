import { createElement } from 'react';
import nodes from './icon-nodes.json';

export function Icon({ name, size = 18 }: { name: keyof typeof nodes; size?: number }) {
  return createElement('svg', { viewBox: '0 0 24 24', width: size, height: size, fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true },
    ...(nodes[name] as [string, object][]).map(([tag, props], key) => createElement(tag, { ...props, key })));
}
