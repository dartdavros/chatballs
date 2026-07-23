import { FormField, KeyValue, SelectField } from "../../shared/form-controls";
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
  name,
  departmentId,
  productId,
  onNameChange,
  onDepartmentChange,
  onProductChange,
}: {
  channel: Channel;
  departments: Department[];
  products: Product[];
  editing: boolean;
  canEditName: boolean;
  canEditDepartment: boolean;
  canEditProduct: boolean;
  allowNoDepartment: boolean;
  name: string;
  departmentId: number | null;
  productId: number | null;
  onNameChange: (value: string) => void;
  onDepartmentChange: (value: number | null) => void;
  onProductChange: (value: number | null) => void;
}) {
  return (
    <section className="channel-card-section">
      <header>
        <h3>Назначение</h3>
        <span>Отдел и продукт канала</span>
      </header>

      {editing ? (
        <div className="channel-assignment">
          {canEditName && <FormField label="Название" value={name} onChange={onNameChange} />}
          {canEditDepartment ? (
            <SelectField label="Отдел" value={departmentId === null ? "" : String(departmentId)} onChange={(value) => onDepartmentChange(value ? Number(value) : null)} options={[...(allowNoDepartment ? [["", "Без отдела"] as [string, string]] : []), ...departments.map((item) => [String(item.id), item.name] as [string, string])]} />
          ) : <KeyValue label="Отдел" value={channel.departmentName ?? "Без отдела"} />}
          {canEditProduct ? (
            <SelectField label="Продукт" value={productId === null ? "" : String(productId)} onChange={(value) => onProductChange(value ? Number(value) : null)} options={[["", "— непродуктовый"], ...products.map((item) => [String(item.id), item.name] as [string, string])]} />
          ) : <KeyValue label="Продукт" value={channel.product?.name ?? "— непродуктовый"} />}
        </div>
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
