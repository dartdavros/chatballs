import { createElement, useState } from "react";
import { CircleHelp } from "lucide";
import { Modal } from "antd";
import { Button } from "../../../shared/ui-controls";
import { et } from "./copy";
import { HelpExample } from "./HelpExample";

export type HelpTopic = "external" | "bindings" | "processing" | "initiative" | "data" | "webFields" | "templates" | "capability" | "keys";
export function HelpTrigger({ topic }: { topic: HelpTopic }) {
  const [open, setOpen] = useState(false);
  const title = et(`help.${topic}Title`);
  return <><button type="button" className="ui-icon-button is-bare external-help-trigger"
    aria-label={`${et("help.about")}${title}`} title={`${et("help.about")}${title}`} aria-haspopup="dialog" onClick={() => setOpen(true)}>
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {CircleHelp.map(([tag, attrs], index) => createElement(tag, { ...attrs, key: index }))}</svg>
  </button><Modal className="agent-create-modal external-help-modal" open={open} width={440} centered title={title}
    onCancel={() => setOpen(false)} footer={null} destroyOnHidden>
    <p className="agent-create-lead">{et(`help.${topic}Text`)}</p>
    {topic === "templates" && <div className="external-help-example"><small>{et("help.example")}</small><HelpExample /></div>}
    <div className="agent-create-actions"><Button variant="secondary" onClick={() => setOpen(false)}>{et("help.close")}</Button></div>
  </Modal></>;
}
