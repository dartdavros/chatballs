import React from "react";

/* KnowledgeDocumentEditor — a minimal document editor shell for AI knowledge
   base entries (ADR-HUB-0013 local component): title, meta, and a plain
   textarea body — no rich-text chrome. */
export function KnowledgeDocumentEditor(props) {
  return React.createElement(
    "div",
    { style: { background: "var(--surface-card)", border: "1px solid var(--n-8)", borderRadius: "var(--radius-2xl)", boxShadow: "var(--shadow-sm)", display: "flex", flexDirection: "column" } },
    React.createElement(
      "div",
      { style: { padding: "14px 18px", borderBottom: "1px solid var(--n-9)", display: "flex", alignItems: "center", justifyContent: "space-between" } },
      React.createElement(
        "div",
        null,
        React.createElement("input", {
          value: props.title,
          onChange: props.onTitleChange,
          placeholder: "Название документа",
          style: { border: "none", outline: "none", fontSize: 15, fontWeight: 700, color: "var(--text-heading)", fontFamily: "var(--font-sans)", width: "100%" },
        }),
        React.createElement("div", { style: { fontSize: 11, color: "var(--text-disabled)", marginTop: 3, fontFamily: "var(--font-mono)" } }, props.docId)
      ),
      React.createElement("span", { style: { fontSize: 11.5, color: "var(--text-tertiary)" } }, props.savedLabel ?? "Сохранено")
    ),
    React.createElement("textarea", {
      value: props.body,
      onChange: props.onBodyChange,
      placeholder: "Текст базы знаний…",
      rows: props.rows ?? 10,
      style: { border: "none", outline: "none", resize: "vertical", padding: "16px 18px", fontSize: 13.5, lineHeight: 1.6, color: "var(--text-body)", fontFamily: "var(--font-sans)" },
    })
  );
}
