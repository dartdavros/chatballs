import type { AppData, RouteKey } from "../../types";
import { Icon } from "../../shared/icons";
import { PageHeader, ProductTag } from "../../shared/ui";
import { commandCenterModel, StatusLabel } from "../command/CommandCenter";
import { formatRubMinor, useDepartmentStats } from "./useDepartmentStats";

export function DepartmentsPage({ data, setRoute }: { data: AppData; setRoute: (route: RouteKey) => void }) {
  const sales = data.departments.find((department) => department.code === "sales") ?? data.departments[0];
  const support = data.departments.find((department) => department.code === "support");
  const salesProducts = data.products.filter((product) => product.departments.some((department) => department.code === "sales"));
  const supportProducts = data.products.filter((product) => product.departments.some((department) => department.code === "support"));
  // Реальные операционные метрики отдела продаж (без выдуманных чисел).
  const stats = useDepartmentStats();
  const openDialogs = stats ? String(stats.openDialogs) : "—";
  const salesCount = stats ? String(stats.sales) : "—";
  const revenue = stats ? formatRubMinor(stats.revenueMinor) : "—";
  // Ответственный отдела: первый активный оператор этого отдела (или «—»).
  const salesOwner = data.employees.find((employee) => employee.department === "sales" && !employee.isBlocked);
  const supportOwner = data.employees.find((employee) => employee.department === "support" && !employee.isBlocked);

  return (
    <>
      <PageHeader title="Отделы" text={`Отделы компании · ${data.departments.length} активный(х)`} />
      <div className="departments-grid">
        {sales && (
          <section className="department-card">
            <div className="department-card-header">
              <div className="dept-icon"><Icon name="shop" size={24} /></div>
              <div className="department-card-title">
                <div>
                  <h2>{sales.name}</h2>
                  <StatusLabel vm={commandCenterModel("today")} />
                </div>
                <p>Публичные входящие обращения: лиды, контакты, продажи.</p>
              </div>
            </div>

            <div className="department-meta">
              <div>
                <span>Ответственный</span>
                <strong className="owner-person">{salesOwner ? <><i>{initialsOf(salesOwner.fullName, salesOwner.email)}</i>{salesOwner.fullName || salesOwner.email}</> : "—"}</strong>
              </div>
              <div>
                <span>Состав</span>
                <strong>{sales.memberCount} сотрудник(ов) · {sales.operatorCount} операторов · {sales.agentCount} AI-агент(ов)</strong>
              </div>
              <div>
                <span>Связанные продукты</span>
                <strong className="product-tags">{salesProducts.map((product) => <ProductTag product={product} key={product.id} />)}</strong>
              </div>
            </div>

            <div className="department-stats">
              <div><span>Открытые диалоги</span><strong>{openDialogs}</strong></div>
              <div><span>Продажи · сегодня</span><strong>{salesCount}</strong></div>
              <div><span>Выручка</span><strong className="success">{revenue}</strong></div>
            </div>

            <div className="department-action">
              <button type="button" onClick={() => setRoute("salesOverview")}>Открыть отдел<Icon name="arrow" size={16} /></button>
            </div>
          </section>
        )}

        {support && (
          <section className="department-card">
            <div className="department-card-header">
              <div className="dept-icon"><Icon name="wrench" size={24} /></div>
              <div className="department-card-title">
                <div>
                  <h2>{support.name}</h2>
                  <StatusLabel vm={commandCenterModel("today")} />
                </div>
                <p>Обслуживание существующих клиентов продуктов через авторизованный чат.</p>
              </div>
            </div>

            <div className="department-meta">
              <div>
                <span>Ответственный</span>
                <strong className="owner-person">{supportOwner ? <><i>{initialsOf(supportOwner.fullName, supportOwner.email)}</i>{supportOwner.fullName || supportOwner.email}</> : "—"}</strong>
              </div>
              <div>
                <span>Состав</span>
                <strong>{support.memberCount} сотрудник(ов) · {support.operatorCount} операторов · {support.agentCount} AI-агент(ов)</strong>
              </div>
              <div>
                <span>Связанные продукты</span>
                <strong className="product-tags">{supportProducts.map((product) => <ProductTag product={product} key={product.id} />)}</strong>
              </div>
            </div>

            <div className="department-stats">
              <div><span>Открытые обращения</span><strong>—</strong></div>
              <div><span>Ожидают оператора</span><strong>—</strong></div>
              <div><span>Обслуживаются AI</span><strong>—</strong></div>
            </div>

            <div className="department-action">
              <button type="button" onClick={() => setRoute("supportOverview")}>Открыть отдел<Icon name="arrow" size={16} /></button>
            </div>
          </section>
        )}
      </div>
    </>
  );
}

function initialsOf(fullName: string, email: string): string {
  const source = fullName || email;
  if (!source) return "?";
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return source.slice(0, 2).toUpperCase();
}
