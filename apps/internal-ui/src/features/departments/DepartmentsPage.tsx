import type { AppData, RouteKey } from "../../types";
import { Icon } from "../../shared/icons";
import { PageHeader, ProductTag } from "../../shared/ui";
import { commandCenterModel, StatusLabel } from "../command/CommandCenter";

export function DepartmentsPage({ data, setRoute }: { data: AppData; setRoute: (route: RouteKey) => void }) {
  const sales = data.departments.find((department) => department.code === "sales") ?? data.departments[0];
  return (
    <>
      <PageHeader title="Отделы" text={`Существующие отделы компании · ${data.departments.length} активный`} />
      {sales && (
        <div className="departments-grid">
          <section className="department-card">
            <div className="department-card-header">
              <div className="dept-icon"><Icon name="shop" size={24} /></div>
              <div className="department-card-title">
                <div>
                  <h2>{sales.name}</h2>
                  <StatusLabel vm={commandCenterModel("today")} />
                </div>
                <p>AI ведёт большинство диалогов, очередь оператора пуста.</p>
              </div>
            </div>

            <div className="department-meta">
              <div>
                <span>Ответственный</span>
                <strong className="owner-person"><i>АК</i>Анна Котова</strong>
              </div>
              <div>
                <span>Состав</span>
                <strong>4 сотрудника · 1 AI-агент</strong>
              </div>
              <div>
                <span>Связанные продукты</span>
                <strong className="product-tags">{data.products.map((product) => <ProductTag product={product} key={product.id} />)}</strong>
              </div>
            </div>

            <div className="department-stats">
              <div><span>Открытые диалоги</span><strong>42</strong></div>
              <div><span>Продажи · сегодня</span><strong>18</strong></div>
              <div><span>Выручка</span><strong className="success">₽146 200</strong></div>
            </div>

            <div className="department-action">
              <button type="button" onClick={() => setRoute("salesOverview")}>Открыть отдел<Icon name="arrow" size={16} /></button>
            </div>
          </section>
        </div>
      )}
      <p className="muted-note">Новые отделы появятся здесь по мере их создания.</p>
    </>
  );
}
