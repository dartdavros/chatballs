import { ContextSection } from "../../conversations/ContextSection";
import { FieldRow } from "../../conversations/FieldRow";
import type { ApiConversation, OperatorCard, OperatorCardField } from "../../conversations/model";

// Renderer правой панели оператора по operator_cards из Product Support Identity
// Contract (ADR-HUB-0022 §8.3 / SPEC-HUB-0011 §8). Карточки не хардкодятся —
// рендерятся динамически по snapshot.operatorContextJson.operator_cards[].
// Типы: text/email/phone/url/code/badge/datetime/boolean/number; unknown→text.
export function OperatorCards({ detail }: { detail: ApiConversation | null }) {
  const snapshot = detail?.supportIdentitySnapshot ?? null;
  if (!snapshot) {
    return <div className="sales-client-context"><p className="sales-context-muted">Контрактный контекст недоступен</p></div>;
  }

  const cards = snapshot.operatorContextJson?.operator_cards ?? [];
  const hero = snapshot.displayName || `client:${snapshot.subjectKey.slice(0, 8)}`;
  return (
    <div className="sales-client-context">
      <div className="sales-client-hero"><span style={{ background: "#9254de" }}>{initialsOf(hero)}</span><strong>{hero}</strong></div>

      <ContextSection title="КОНТРАКТ">
        <FieldRow title="Subject" text={snapshot.subjectKey} mono note={snapshot.contractCode} />
        {snapshot.accountKey && <FieldRow title="Account" text={snapshot.accountKey} mono />}
      </ContextSection>

      {cards.map((card) => (
        <OperatorCardSection card={card} key={card.title} />
      ))}
    </div>
  );
}

function OperatorCardSection({ card }: { card: OperatorCard }) {
  return (
    <ContextSection title={card.title.toUpperCase()}>
      {card.fields.length === 0 && <p className="sales-context-muted">Нет данных</p>}
      {card.fields.map((field) => <OperatorField field={field} key={field.label} />)}
    </ContextSection>
  );
}

function OperatorField({ field }: { field: OperatorCardField }) {
  const value = field.value;
  if (value == null || value === "") {
    return <FieldRow title={field.label} text="—" muted />;
  }
  switch (field.type) {
    case "email":
      return <FieldRow icon="mail" title={field.label} text={String(value)} mono />;
    case "phone":
      return <FieldRow icon="phone" title={field.label} text={String(value)} />;
    case "url":
      return <FieldRow title={field.label} text={String(value)} mono />;
    case "code":
      return <FieldRow title={field.label} text={String(value)} mono />;
    case "badge":
      return <FieldRow dot="#1677ff" title={field.label} text={String(value)} />;
    case "boolean":
      return <FieldRow dot={value ? "#389e0d" : "#bfbfbf"} title={field.label} text={value ? "да" : "нет"} />;
    case "number":
      return <FieldRow title={field.label} text={String(value)} />;
    case "datetime":
      return <FieldRow title={field.label} text={fmtDateTime(value)} />;
    // text и unknown → text (SPEC-HUB-0011 §8: unknown тип → text, логируется warning).
    default:
      return <FieldRow title={field.label} text={String(value)} />;
  }
}

function fmtDateTime(value: unknown): string {
  const str = String(value);
  const parsed = new Date(str);
  return Number.isNaN(parsed.getTime()) ? str : parsed.toLocaleString("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  return (parts[0][0] + (parts[1]?.[0] ?? "")).toUpperCase();
}
