import { useState } from "react";

import { Button } from "../../../shared/ui-controls";

type ActionKey = "correct" | "partial-refund" | "refund" | "cancel";

const ACTIONS: Array<{ key: ActionKey; label: string; variant: "secondary" | "danger-outline"; amount: boolean }> = [
  { key: "correct", label: "Исправить сумму", variant: "secondary", amount: true },
  { key: "partial-refund", label: "Частичный возврат", variant: "secondary", amount: true },
  { key: "refund", label: "Полный возврат", variant: "danger-outline", amount: false },
  { key: "cancel", label: "Отменить продажу", variant: "danger-outline", amount: false },
];

// Действия не проводят платёж и не выдают продукт (SPEC §8.2): каждое лишь
// фиксирует новое SaleEvent. Физическое удаление продажи запрещено.
export function SaleActionPanel({
  busy,
  actionError,
  onCorrect,
  onPartialRefund,
  onRefund,
  onCancel,
}: {
  busy: boolean;
  actionError: string;
  onCorrect: (amountMinor: number, reason: string) => void;
  onPartialRefund: (refundedAmountMinor: number, reason: string) => void;
  onRefund: (reason: string) => void;
  onCancel: (reason: string) => void;
}) {
  const [active, setActive] = useState<ActionKey | null>(null);
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");

  const current = ACTIONS.find((action) => action.key === active) ?? null;

  function reset() {
    setActive(null);
    setAmount("");
    setReason("");
  }

  function submit() {
    if (!reason.trim()) return;
    const minor = Math.round(Number(amount.replace(/\s/g, "").replace(",", ".")) * 100);
    if (active === "correct") onCorrect(minor, reason.trim());
    else if (active === "partial-refund") onPartialRefund(minor, reason.trim());
    else if (active === "refund") onRefund(reason.trim());
    else if (active === "cancel") onCancel(reason.trim());
    reset();
  }

  return (
    <section className="ai-card order-detail-actions">
      <h3>Действия</h3>
      <div className="order-detail-action-row">
        {ACTIONS.map((action) => (
          <Button key={action.key} variant={action.variant} disabled={busy} onClick={() => setActive(action.key)}>{action.label}</Button>
        ))}
      </div>

      {current && (
        <div className="sale-action-form">
          {current.amount && (
            <label className="sale-action-field">
              <span>{current.key === "partial-refund" ? "Сумма возврата, ₽" : "Новая сумма, ₽"}</span>
              <input value={amount} onChange={(event) => setAmount(event.target.value)} inputMode="decimal" placeholder="0" />
            </label>
          )}
          <label className="sale-action-field wide">
            <span>Основание</span>
            <input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Причина изменения" />
          </label>
          <div className="sale-action-buttons">
            <Button variant="secondary" onClick={reset} disabled={busy}>Отмена</Button>
            <Button variant="primary" onClick={submit} disabled={busy || !reason.trim() || (current.amount && !amount.trim())}>Подтвердить</Button>
          </div>
        </div>
      )}

      {actionError && <div className="sale-action-error">{actionError}</div>}
    </section>
  );
}
