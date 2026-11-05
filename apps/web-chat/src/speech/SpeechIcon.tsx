import { createElement } from "react";
import { Mic, RotateCcw, Square, X, type IconNode } from "lucide";

const nodes: Record<string, IconNode> = { mic: Mic, refresh: RotateCcw, stop: Square, close: X };

export function SpeechIcon({ name }: { name: keyof typeof nodes }) {
  return <svg viewBox="0 0 24 24" width="17" height="17" fill={name === "stop" ? "currentColor" : "none"}
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {nodes[name].map(([tag, attributes], index) => createElement(tag, { ...attributes, key: index }))}
  </svg>;
}
