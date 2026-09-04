import { FormField, KeyValue, SelectField } from "../../shared/form-controls";
import { formatDate } from "../../shared/utils";
import type { EmployeeGroup, Product } from "../../types";
import type { Channel } from "./types";

/**
 * Группа и продукт канала.
 *
 * По умолчанию секция read-only: правка включается кнопкой «Изменить» в шапке
 * и применяется одним сохранением. Так смена продукта не уходит на сервер от
 * случайного выбора в списке — она меняет доступные флаги политики.
 */
export function ChannelAssignmentSection({
  channel,
  groups,
  products,
  editing,
  canEditName,
  canEditGroup,
  canEditProduct,
  name,
  groupId,
  productId,
  onNameChange,
  onGroupChange,
  onProductChange,
}: {
  channel: Channel;
  groups: EmployeeGroup[];
  products: Product[];
  editing: boolean;
  canEditName: boolean;
  canEditGroup: boolean;
  canEditProduct: boolean;
  name: string;
  groupId: number | null;
  productId: number | null;
  onNameChange: (value: string) => void;
  onGroupChange: (value: number | null) => void;
  onProductChange: (value: number | null) => void;
}) {
  return (
    <section className="channel-card-section">
      <header>
        <h3>Назначение</h3>
        <span>Группа определяет, какие сотрудники видят диалоги канала; без группы диалоги видны всем</span>
      </header>

      {editing ? (
        <div className="channel-assignment">
          {canEditName && <FormField label="Название" value={name} onChange={onNameChange} />}
          {canEditGroup ? (
            <SelectField label="Группа" value={groupId === null ? "" : String(groupId)} onChange={(value) => onGroupChange(value ? Number(value) : null)} options={[["", "Без группы"] as [string, string], ...groups.map((item) => [String(item.id), item.name] as [string, string])]} />
          ) : <KeyValue label="Группа" value={channel.groupName ?? "Без группы"} />}
          {canEditProduct ? (
            <SelectField label="Продукт" value={productId === null ? "" : String(productId)} onChange={(value) => onProductChange(value ? Number(value) : null)} options={[["", "— непродуктовый"], ...products.map((item) => [String(item.id), item.name] as [string, string])]} />
          ) : <KeyValue label="Продукт" value={channel.product?.name ?? "— непродуктовый"} />}
        </div>
      ) : (
        <div className="channel-assignment">
          <KeyValue label="Группа" value={channel.groupName ?? "Без группы"} />
          <KeyValue label="Продукт" value={channel.product?.name ?? "— непродуктовый"} />
          <KeyValue label="Код" value={<code>{channel.code}</code>} />
          <KeyValue label="Создан" value={formatDate(channel.createdAt)} />
        </div>
      )}
    </section>
  );
}
