import { Modal } from "antd";
import { useEffect, useState } from "react";

import { api } from "../../../api/client";
import { FormField, SelectField, TextAreaField } from "../../../shared/form-controls";
import { Button } from "../../../shared/ui-controls";
import type { Product } from "../../../types";

type ClientOption = { id: number; name: string };

type SaleForm = {
  contactId: string;
  productCode: string;
  amount: string;
  currency: string;
  externalSaleId: string;
  reason: string;
};

const emptyForm: SaleForm = { contactId: "", productCode: "", amount: "", currency: "RUB", externalSaleId: "", reason: "" };

// Ручная фиксация подтверждённой внешней продажи (SPEC-HUB-0014 §7). Это fallback:
// создаётся SaleEvent(source=MANUAL) через тот же application service, что и API.
export function AddSaleDialog({ products, open, onClose, onSaved }: { products: Product[]; open: boolean; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState<SaleForm>(emptyForm);
  const [clients, setClients] = useState<ClientOption[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setForm({ ...emptyForm, productCode: products[0]?.code ?? "" });
    setError("");
    api<{ items: ClientOption[] }>("/api/v1/conversations/clients/")
      .then((data) => setClients(data.items.map((client) => ({ id: client.id, name: client.name }))))
      .catch(() => setClients([]));
  }, [open, products]);

  function update(field: keyof SaleForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit() {
    const amountValue = Number(form.amount.replace(/\s/g, "").replace(",", "."));
    if (!form.contactId || !form.productCode) {
      setError("Выберите клиента и продукт");
      return;
    }
    if (!Number.isFinite(amountValue) || amountValue < 0) {
      setError("Укажите корректную сумму");
      return;
    }
    if (!form.reason.trim()) {
      setError("Укажите основание продажи");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await api("/api/v1/sales/", {
        method: "POST",
        body: JSON.stringify({
          contactId: Number(form.contactId),
          productCode: form.productCode,
          amountMinor: Math.round(amountValue * 100),
          currency: form.currency.trim().toUpperCase() || "RUB",
          externalSaleId: form.externalSaleId.trim(),
          reason: form.reason.trim(),
        }),
      });
      await onSaved();
      onClose();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal className="product-form-modal" open={open} onCancel={onClose} footer={null} title="Добавить продажу" destroyOnHidden>
      <div className="product-form-grid">
        <SelectField label="Клиент" value={form.contactId} onChange={(value) => update("contactId", value)} options={[["", "— выберите —"], ...clients.map((client): [string, string] => [String(client.id), client.name])]} />
        <SelectField label="Продукт" value={form.productCode} onChange={(value) => update("productCode", value)} options={products.map((product): [string, string] => [product.code, product.name])} />
        <FormField label="Сумма" value={form.amount} onChange={(value) => update("amount", value)} />
        <FormField label="Валюта" value={form.currency} onChange={(value) => update("currency", value)} mono />
        <FormField label="Внешний ID продажи (необязательно)" value={form.externalSaleId} onChange={(value) => update("externalSaleId", value)} mono wide />
        <TextAreaField label="Основание" value={form.reason} onChange={(value) => update("reason", value)} />
      </div>
      {error && <div className="product-form-error">{error}</div>}
      <div className="product-form-actions">
        <Button variant="secondary" onClick={onClose}>Отмена</Button>
        <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Сохранение" : "Создать продажу"}</Button>
      </div>
    </Modal>
  );
}
