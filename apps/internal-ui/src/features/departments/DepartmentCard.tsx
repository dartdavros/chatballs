import type { ReactNode } from "react";

import { Icon } from "../../shared/icons";
import { formatRussianCount } from "../../shared/text";
import { Avatar, ProductTag } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import type { Employee, Product } from "../../types";
import { StatusLabel } from "../command/CommandCenter";
import { departmentCopy } from "./model";

export type DepartmentCardVm = {
  id: number;
  code: string;
  name: string;
  memberCount: number;
  operatorCount: number;
  agentCount: number;
  status: Parameters<typeof StatusLabel>[0]["status"] | null;
  owner: Employee | null;
  products: Product[];
  stats: [ReactNode, ReactNode, ReactNode];
  onOpen: (() => void) | null;
};

export function DepartmentCard({ department }: { department: DepartmentCardVm }) {
  const copy = departmentCopy(department.code);

  return (
    <section className="department-card">
      <div className="department-card-header">
        <div className="dept-icon"><Icon name={copy.icon} size={24} /></div>
        <div className="department-card-title">
          <div>
            <h2>{department.name}</h2>
            {department.status && <StatusLabel status={department.status} />}
          </div>
          <p>{copy.description}</p>
        </div>
      </div>

      <div className="department-meta">
        <div>
          <span>Ответственный</span>
          <strong className="owner-person">
            {department.owner ? <><Avatar employee={department.owner} />{department.owner.fullName || department.owner.email}</> : "—"}
          </strong>
        </div>
        <div>
          <span>Состав</span>
          <strong>
            {formatRussianCount(department.memberCount, "сотрудник", "сотрудника", "сотрудников")}
            {" · "}
            {formatRussianCount(department.operatorCount, "оператор", "оператора", "операторов")}
            {" · "}
            {formatRussianCount(department.agentCount, "AI-агент", "AI-агента", "AI-агентов")}
          </strong>
        </div>
        <div>
          <span>Связанные продукты</span>
          <strong className="product-tags">
            {department.products.length ? department.products.map((product) => <ProductTag product={product} key={product.id} />) : "—"}
          </strong>
        </div>
      </div>

      <div className="department-stats">
        {copy.statLabels.map((label, index) => (
          <div key={label}>
            <span>{label}</span>
            <strong className={index === 2 && department.code === "sales" ? "success" : ""}>{department.stats[index]}</strong>
          </div>
        ))}
      </div>

      {department.onOpen && (
        <div className="department-action">
          <Button variant="primary" icon="arrow" onClick={department.onOpen}>Перейти</Button>
        </div>
      )}
    </section>
  );
}
