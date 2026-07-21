import { Dropdown } from "antd";
import { useState } from "react";

import { Icon } from "../../../shared/icons";
import type { KnowledgeDepartmentReference } from "./types";

export function KnowledgeDepartmentPicker({
  departments,
  disabled = false,
  selectedIds,
  onChange,
}: {
  departments: KnowledgeDepartmentReference[];
  disabled?: boolean;
  selectedIds: number[];
  onChange: (departmentIds: number[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const selected = departments.filter((department) => selectedIds.includes(department.id));

  function toggle(id: number) {
    onChange(selectedIds.includes(id)
      ? selectedIds.filter((item) => item !== id)
      : [...selectedIds, id]);
  }

  const items = departments.map((department) => ({
    key: String(department.id),
    label: (
      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          toggle(department.id);
        }}
      >
        <span className={selectedIds.includes(department.id) ? "selected" : ""}>
          {selectedIds.includes(department.id) && <Icon name="check" size={13} />}
        </span>
        {department.name}
      </button>
    ),
  }));

  return (
    <label className="knowledge-editor-field knowledge-departments-field">
      <span>Отделы <small>— знание доступно агентам этих отделов</small></span>
      <div className="knowledge-department-picker">
        <div className="knowledge-department-picker-value">
          {selected.map((department) => (
            <span className="knowledge-department-chip" key={department.id}>
              <i />{department.name}
              <button aria-label={`Удалить отдел ${department.name}`} disabled={disabled} type="button" onClick={() => toggle(department.id)}>
                <Icon name="xCircle" size={13} />
              </button>
            </span>
          ))}
          <Dropdown menu={{ items }} open={open} onOpenChange={setOpen} trigger={["click"]} overlayClassName="app-dropdown is-wide knowledge-department-dropdown">
            <button className="knowledge-add-department" disabled={disabled} type="button">
              <Icon name="plus" size={13} />Добавить отдел
            </button>
          </Dropdown>
        </div>
      </div>
    </label>
  );
}
