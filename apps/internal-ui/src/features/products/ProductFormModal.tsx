import { Modal } from "antd";
import { useEffect, useState } from "react";

import { api } from "../../api/client";
import { FormField, SelectField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import type { Department, Product } from "../../types";

type ProductForm = {
  code: string;
  name: string;
  siteUrl: string;
  departmentId: string;
};

const emptyForm: ProductForm = { code: "", name: "", siteUrl: "", departmentId: "" };

export function ProductFormModal({ departments, open, product, onClose, onSaved }: { departments: Department[]; open: boolean; product?: Product; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState<ProductForm>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setForm(product ? {
      code: product.code,
      name: product.name,
      siteUrl: product.siteUrl,
      departmentId: String(product.departments[0]?.id ?? departments[0]?.id ?? ""),
    } : { ...emptyForm, departmentId: String(departments[0]?.id ?? "") });
    setError("");
  }, [departments, open, product]);

  function update(field: keyof ProductForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit() {
    if (!form.code.trim() || !form.name.trim()) {
      setError("Заполните код и название продукта");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const body = JSON.stringify({
        code: form.code,
        name: form.name,
        siteUrl: form.siteUrl,
        departmentIds: form.departmentId ? [Number(form.departmentId)] : [],
      });
      await api(product ? `/api/v1/company/products/${product.id}/update/` : "/api/v1/company/products/create/", { method: product ? "PATCH" : "POST", body });
      await onSaved();
      onClose();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal className="product-form-modal" open={open} onCancel={onClose} footer={null} title={product ? "Редактировать продукт" : "Создать продукт"} destroyOnHidden>
      <div className="product-form-grid">
        <FormField label="Название" value={form.name} onChange={(value) => update("name", value)} />
        <FormField label="Код" value={form.code} onChange={product ? undefined : (value) => update("code", value)} disabled={Boolean(product)} mono />
        <FormField label="Сайт" value={form.siteUrl} onChange={(value) => update("siteUrl", value)} wide />
        <SelectField label="Отдел" value={form.departmentId} onChange={(value) => update("departmentId", value)} options={departments.map((department) => [String(department.id), department.name])} />
      </div>
      {error && <div className="product-form-error">{error}</div>}
      <div className="product-form-actions">
        <Button variant="secondary" onClick={onClose}>Отмена</Button>
        <Button variant="primary" onClick={submit} disabled={saving}>{saving ? "Сохранение" : "Сохранить"}</Button>
      </div>
    </Modal>
  );
}
