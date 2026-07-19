import { useEffect, useRef, useState } from "react";

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
  const root = useRef<HTMLDivElement>(null);
  const selected = departments.filter((department) => selectedIds.includes(department.id));

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  function toggle(id: number) {
    onChange(selectedIds.includes(id)
      ? selectedIds.filter((item) => item !== id)
      : [...selectedIds, id]);
  }

  return (
    <label className="knowledge-editor-field knowledge-departments-field">
      <span>Отделы <small>— знание доступно агентам этих отделов</small></span>
      <div className="knowledge-department-picker" ref={root}>
        <div className="knowledge-department-picker-value">
          {selected.map((department) => (
            <span className="knowledge-department-chip" key={department.id}>
              <i />{department.name}
              <button aria-label={`Удалить отдел ${department.name}`} disabled={disabled} type="button" onClick={() => toggle(department.id)}>
                <Icon name="xCircle" size={13} />
              </button>
            </span>
          ))}
          <button className="knowledge-add-department" disabled={disabled} type="button" onClick={() => setOpen((value) => !value)}>
            <Icon name="plus" size={13} />Добавить отдел
          </button>
        </div>
        {open && (
          <div className="knowledge-department-menu">
            {departments.map((department) => (
              <button className={selectedIds.includes(department.id) ? "selected" : ""} type="button" key={department.id} onClick={() => toggle(department.id)}>
                <span><Icon name="check" size={13} /></span>{department.name}
              </button>
            ))}
          </div>
        )}
      </div>
    </label>
  );
}
