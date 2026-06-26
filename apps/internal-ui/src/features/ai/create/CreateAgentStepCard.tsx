import type { ReactNode } from "react";

export function CreateAgentStepCard({ number, title, text, children }: { number: number; title: string; text: string; children: ReactNode }) {
  return (
    <section className="ai-create-step">
      <div className="ai-create-step-title">
        <span>{number}</span>
        <h3>{title}</h3>
      </div>
      <p>{text}</p>
      {children}
    </section>
  );
}
