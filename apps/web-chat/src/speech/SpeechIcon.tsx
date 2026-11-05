import { createElement } from "react";
import { Mic, RotateCcw, Square, X, Volume2, Play, Pause, type IconNode } from "lucide";

const nodes: Record<string, IconNode> = { mic: Mic, refresh: RotateCcw, stop: Square, close: X, sound: Volume2, play: Play, pause: Pause };

export function SpeechIcon({ name, size = 17 }: { name: keyof typeof nodes; size?: number }) {
  return <svg viewBox="0 0 24 24" width={size} height={size} fill={name === "stop" ? "currentColor" : "none"}
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {nodes[name].map(([tag, attributes], index) => createElement(tag, { ...attributes, key: index }))}
  </svg>;
}
