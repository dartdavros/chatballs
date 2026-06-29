import { Modal } from "antd";
import { useEffect, useState } from "react";

import { FormField, SelectField, SwitchButton, TextAreaField } from "../../../shared/form-controls";
import { Button } from "../../../shared/ui-controls";
import type { ProductOffer } from "../../../types";
import { createOffer, fulfillmentOptions, paymentOptions, updateOffer, type OfferBody } from "./offerApi";

type OfferForm = {
  code: string;
  name: string;
  description: string;
  fulfillmentType: string;
  paymentType: string;
  isActive: boolean;
  aiOfferable: boolean;
  primaryBoxOfferId: string;
};

const emptyForm: OfferForm = {
  code: "",
  name: "",
  description: "",
  fulfillmentType: "SAAS_ACCESS",
  paymentType: "ONE_TIME",
  isActive: true,
  aiOfferable: false,
  primaryBoxOfferId: "",
};

export function OfferFormModal({ productId, offers, offer, open, onClose, onSaved }: { productId: number; offers: ProductOffer[]; offer?: ProductOffer; open: boolean; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState<OfferForm>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setForm(offer ? {
      code: offer.code,
      name: offer.name,
      description: offer.description,
      fulfillmentType: offer.fulfillmentType,
      paymentType: offer.paymentType,
      isActive: offer.isActive,
      aiOfferable: offer.aiOfferable,
      primaryBoxOfferId: offer.primaryBoxOfferId ? String(offer.primaryBoxOfferId) : "",
    } : emptyForm);
    setError("");
  }, [offer, open]);

  function update<K extends keyof OfferForm>(field: K, value: OfferForm[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  const boxOffers = offers.filter((item) => item.fulfillmentType === "BOX_LICENSE" && item.id !== offer?.id);
  const isSupport = form.fulfillmentType === "SUPPORT_EXTENSION";

  async function submit() {
    if (!form.name.trim() || (!offer && !form.code.trim())) {
      setError("Заполните код и название предложения");
      return;
    }
    const body: OfferBody = {
      name: form.name,
      description: form.description,
      fulfillmentType: form.fulfillmentType,
      paymentType: form.paymentType,
      isActive: form.isActive,
      aiOfferable: form.aiOfferable,
      primaryBoxOfferId: isSupport && form.primaryBoxOfferId ? Number(form.primaryBoxOfferId) : null,
      ...(offer ? {} : { code: form.code }),
    };
    setSaving(true);
    setError("");
    try {
      if (offer) await updateOffer(productId, offer.id, body);
      else await createOffer(productId, body);
      await onSaved();
      onClose();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal className="product-form-modal" open={open} onCancel={onClose} footer={null} title={offer ? "Редактировать предложение" : "Новое предложение"} destroyOnHidden>
      <div className="product-form-grid">
        <FormField label="Название" value={form.name} onChange={(value) => update("name", value)} />
        <FormField label="Код" value={form.code} onChange={offer ? undefined : (value) => update("code", value)} disabled={Boolean(offer)} mono />
        <SelectField label="Способ исполнения" value={form.fulfillmentType} onChange={(value) => update("fulfillmentType", value)} options={fulfillmentOptions} />
        <SelectField label="Тип оплаты" value={form.paymentType} onChange={(value) => update("paymentType", value)} options={paymentOptions} />
        {isSupport && (
          <SelectField label="Базовое коробочное предложение" value={form.primaryBoxOfferId} onChange={(value) => update("primaryBoxOfferId", value)} options={[["", "— выберите —"], ...boxOffers.map((item) => [String(item.id), item.name] as [string, string])]} />
        )}
        <TextAreaField label="Описание" value={form.description} onChange={(value) => update("description", value)} />
      </div>
      <div className="offer-form-switches">
        <label><SwitchButton checked={form.isActive} onClick={() => update("isActive", !form.isActive)} className="ui-switch" label="Активно" /><span>Активно</span></label>
        <label><SwitchButton checked={form.aiOfferable} onClick={() => update("aiOfferable", !form.aiOfferable)} className="ui-switch" label="AI может предлагать" /><span>AI может предлагать</span></label>
      </div>
      {error && <div className="product-form-error">{error}</div>}
      <div className="product-form-actions">
        <Button variant="secondary" onClick={onClose}>Отмена</Button>
        <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Сохранение" : "Сохранить"}</Button>
      </div>
    </Modal>
  );
}
