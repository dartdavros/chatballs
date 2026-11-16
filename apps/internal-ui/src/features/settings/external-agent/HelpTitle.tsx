import { HelpTrigger, type HelpTopic } from "./HelpTrigger";

export function HelpTitle({ title, topic }: { title: string; topic: HelpTopic }) {
  return <span className="external-help-title"><strong>{title}</strong><HelpTrigger topic={topic} /></span>;
}
