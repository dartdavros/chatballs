export type ChatProposal = {open: string; download: string; openLabel: string; downloadLabel: string};

function localDocumentPath(path: string) {
  return /^\/api\/v1\/demo-local\/proposals\/[A-Za-z0-9_.:-]+\/(?:\?download=1)?$/.test(path) ? path : undefined;
}

export function ChatProposalDocument({document, text}: {document: ChatProposal; text: string}) {
  const open = localDocumentPath(document.open);
  const download = localDocumentPath(document.download);
  return <>{text}{open && download && <div>
    <a href={open} target="_blank" rel="noopener noreferrer">{document.openLabel}</a>{" · "}
    <a href={download} download>{document.downloadLabel}</a>
  </div>}</>;
}
