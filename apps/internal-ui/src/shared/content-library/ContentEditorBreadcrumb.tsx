export function ContentEditorBreadcrumb({
  backLabel,
  category,
  title,
  onBack,
}: {
  backLabel: string;
  category?: string;
  title: string;
  onBack: () => void;
}) {
  return (
    <div className="knowledge-editor-breadcrumb">
      <button type="button" onClick={onBack}>{backLabel}</button>
      {category && <><span>/</span><em>{category}</em></>}
      <span>/</span>
      <strong>{title}</strong>
    </div>
  );
}
