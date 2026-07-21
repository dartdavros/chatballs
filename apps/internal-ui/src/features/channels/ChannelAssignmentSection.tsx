import { useState } from "react";

import { FormField, KeyValue, SelectField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import { formatDate } from "../../shared/utils";
import type { Department, Product } from "../../types";
import type { Channel } from "./types";

/**
 * Отдел и продукт канала.
 *
 * По умолчанию секция read-only: правка включается кнопкой «Изменить» в шапке
 * и применяется одним сохранением. Так смена продукта не уходит на сервер от
 * случайного выбора в списке — она меняет доступные флаги политики.
 */
export function ChannelAssignmentSection({
  channel,
  departments,
  products,
  editing,
  canEditName,
  canEditDepartment,
  canEditProduct,
  allowNoDepartment,
  busy,
  onSave,
  onCancel,
}: {
  channel: Channel;
  departments: Department[];
  products: Product[];
  editing: boolean;
  canEditName: boolean;
  canEditDepartment: boolean;
  canEditProduct: boolean;
  allowNoDepartment: boolean;
  busy: boolean;
  onSave: (patch: { name?: string; departmentId?: number | null; productId?: number | null }) => void;
  onCancel: () => void;
}) {
  const [departmentId, setDepartmentId] = useState(String(channel.departmentId ?? ""));
  const [productId, setProductId] = useState(String(channel.product?.id ?? ""));
  const [name, setName] = useState(channel.name);

  return (
    <section className="channel-card-section">
      <header>
        <h3>Назначение</h3>
        <span>{editing ? "Изменения применяются одним сохранением" : "Отдел и продукт канала"}</span>
      </header>

      {editing ? (
        <>
          <div className="channel-assignment">
            {canEditName && <FormField label="Название" value={name} onChange={setName} />}
            {canEditDepartment ? (
              <SelectField label="Отдел" value={departmentId} onChange={setDepartmentId} options={[...(allowNoDepartment ? [["", "Без отдела"] as [string, string]] : []), ...departments.map((item) => [String(item.id), item.name] as [string, string])]} />
            ) : <KeyValue label="Отдел" value={channel.departmentName ?? "Без отдела"} />}
            {canEditProduct ? (
              <SelectField label="Продукт" value={productId} onChange={setProductId} options={[["", "— непродуктовый"], ...products.map((item) => [String(item.id), item.name] as [string, string])]} />
            ) : <KeyValue label="Продукт" value={channel.product?.name ?? "— непродуктовый"} />}
          </div>
          <div className="channel-section-actions">
            <Button variant="secondary" onClick={onCancel}>Отмена</Button>
            <Button
              variant="primary"
              disabled={busy || !name.trim()}
              onClick={() => onSave({
                ...(canEditName ? { name: name.trim() } : {}),
                ...(canEditDepartment ? { departmentId: departmentId ? Number(departmentId) : null } : {}),
                ...(canEditProduct ? { productId: productId ? Number(productId) : null } : {}),
              })}
            >
              Сохранить
            </Button>
          </div>
        </>
      ) : (
        <div className="channel-assignment">
          <KeyValue label="Отдел" value={channel.departmentName ?? "Без отдела"} />
          <KeyValue label="Продукт" value={channel.product?.name ?? "— непродуктовый"} />
          <KeyValue label="Код" value={<code>{channel.code}</code>} />
          <KeyValue label="Создан" value={formatDate(channel.createdAt)} />
        </div>
      )}
    </section>
  );
}
