import { useEffect, useState } from "react";
import { Modal } from "antd";
import { PreparedMessage, type PreparedContent } from "@chatballs/ui";
import { api } from "../../../api/client";
import { LogoSpinner } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import { et } from "./copy";
import { pathFor } from "./model";

function Preview({ organization, id, title }: { organization: string; id: string; title: string }) {
  const [content, setContent] = useState<PreparedContent>();
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    api<PreparedContent>(`${pathFor(organization)}templates/${encodeURIComponent(id)}/preview/`, { signal: controller.signal })
      .then(result => { if (!controller.signal.aborted) setContent(result); })
      .catch(() => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, [organization, id]);
  return <div className="external-help-example" style={{ minHeight: 112 }}><small>{et("help.example")}</small>
    {failed ? <p role="alert">{et("policy.templatesStale")}</p> : content ? <PreparedMessage content={content} title={title} />
      : <div role="status"><LogoSpinner size={18} /></div>}
  </div>;
}
export function TemplateMessageLink({ organization, id, title }: { organization: string; id: string; title: string }) {
  const [open, setOpen] = useState(false);
  return <><button type="button" className="link" aria-label={`${et("help.openMessage")}: ${title}`} onClick={() => setOpen(true)}>{et("help.openMessage")}</button>
    <Modal className="agent-create-modal external-help-modal" open={open} width={440} centered title={title}
      onCancel={() => setOpen(false)} footer={null} destroyOnHidden>
      {open && <Preview organization={organization} id={id} title={title} />}
      <div className="agent-create-actions"><Button variant="secondary" onClick={() => setOpen(false)}>{et("help.close")}</Button></div>
    </Modal></>;
}
