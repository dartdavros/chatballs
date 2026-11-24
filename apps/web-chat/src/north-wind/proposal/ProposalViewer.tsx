import { useEffect, useRef, useState } from "react";

import { Icon } from "../Icons";
import { t } from "../language";
import type { ProposalResult } from "./model";
import "./proposal-viewer.css";

export function ProposalViewer({proposal, onClose}: {proposal: ProposalResult["proposal"]; onClose: () => void}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [documentHtml, setDocumentHtml] = useState("");
  const [error, setError] = useState(false);

  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => element?.close();
  }, []);

  useEffect(() => {
    if (!proposal.documentPath.startsWith("/api/v1/demo-local/proposals/")) {
      setError(true);
      return;
    }
    const controller = new AbortController();
    fetch(proposal.documentPath, {signal: controller.signal, redirect: "error", cache: "no-store"}).then(response => {
      if (!response.ok) throw new Error("proposal_unavailable");
      return response.text();
    }).then(setDocumentHtml).catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [proposal.documentPath]);

  const title = t("proposal_document", {number: proposal.number});
  return <dialog ref={dialog} className="proposal-viewer" aria-labelledby="proposal-viewer-title"
    onCancel={event => { event.preventDefault(); onClose(); }}
    onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <header><div><span>{t("proposal_document_brand")}</span><h2 id="proposal-viewer-title">{title}</h2></div>
      <button type="button" className="proposal-viewer-close" onClick={onClose} aria-label={t("proposal_close")}>
        <Icon name="X" size={20} />
      </button>
    </header>
    {error ? <p role="alert">{t("proposal_server_error")}</p> : <iframe title={title} srcDoc={documentHtml} sandbox="" />}
    <footer><span>{t("proposal_document_note")}</span>
      <button type="button" disabled={!proposal.downloadPath.startsWith("/api/v1/demo-local/proposals/")}
        onClick={() => { location.assign(proposal.downloadPath); }}>
        <Icon name="Download" size={16} />{t("proposal_download")}
      </button>
    </footer>
  </dialog>;
}
