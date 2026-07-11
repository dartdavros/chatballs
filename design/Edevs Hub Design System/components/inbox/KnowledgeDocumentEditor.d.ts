import React from "react";

/**
 * @startingPoint section="Inbox" subtitle="Plain-text knowledge base document editor" viewport="700x380"
 */
export interface KnowledgeDocumentEditorProps {
  title: string;
  onTitleChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  docId?: string;
  body: string;
  onBodyChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  rows?: number;
  savedLabel?: string;
}

export function KnowledgeDocumentEditor(props: KnowledgeDocumentEditorProps): JSX.Element;
