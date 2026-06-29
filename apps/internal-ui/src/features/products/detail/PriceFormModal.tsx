import { Modal } from "antd";
import { useEffect, useState } from "react";

import { FormField, SelectField } from "../../../shared/form-controls";
import { Button } from "../../../shared/ui-controls";
import { addPriceVersion, billingOptions } from "./offerApi";

export function PriceFormModal({ productId, offerId, offerName, open, onClose, onSaved }: { productId: number; offerId: number | null; offerName: string; open: boolean; onClose: () => void; onSaved: () => void }) {
  const [amount, setAmount] = useState("");
  const [billingPeriod, setBillingPeriod] = useState("ONE_TIME");
  const [currency, setCurrency] = useState("RUB");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setAmount("");
    setBillingPeriod("ONE_TIME");
    setCurrency("RUB");
    setError("");
  }, [open]);

  async function submit() {
    const value = Number.parseFloat(amount.replace(",", "."));
    if (!Number.isFinite(value) || value < 0) {
      setError("Укажите корректную сумму");
      return;
    }
    if (offerId === null) return;
    setSaving(true);
    setError("");
    try {
      await addPriceVersion(productId, offerId, {
        amountMinor: Math.round(value * 100),
        billingPeriod,
        currency: currency.trim().toUpperCase() || "RUB",
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
    <Modal className="product-form-modal" open={open} onCancel={onClose} footer={null} title={`Новая версия цены · ${offerName}`} destroyOnHidden>
      <p className="product-offers-note">Новая версия архивирует прежнюю активную цену в той же валюте и периоде. Прошлые версии не редактируются.</p>
      <div className="product-form-grid">
        <FormField label="Сумма" value={amount} onChange={setAmount} placeholder="4900" />
        <FormField label="Валюта" value={currency} onChange={setCurrency} mono />
        <SelectField label="Период списания" value={billingPeriod} onChange={setBillingPeriod} options={billingOptions} />
      </div>
      {error && <div className="product-form-error">{error}</div>}
      <div className="product-form-actions">
        <Button variant="secondary" onClick={onClose}>Отмена</Button>
        <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Сохранение" : "Добавить версию"}</Button>
      </div>
    </Modal>
  );
}
