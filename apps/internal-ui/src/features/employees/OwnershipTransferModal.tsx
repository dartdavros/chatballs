import { useEffect, useState } from "react";

import { api } from "../../api/client";
import { Icon } from "../../shared/icons";
import { Avatar } from "../../shared/ui";
import { SearchInput } from "../../shared/ui-controls";
import { useDebounced } from "../../shared/useDebounced";
import type { Employee, Role } from "../../types";
import { fetchOwner, fetchOwnershipCandidates } from "./api";
import { employeeAvatarColor, roleBadge } from "./model";
import { t } from "../../i18n";

// Передача владения (дизайн-базлайн v2, кадр E9). Кандидаты — только активные
// администраторы: чтобы передать сотруднику, его сначала делают админом.

const PREVIOUS_ROLES: Array<{ value: Extract<Role, "ADMIN" | "EMPLOYEE">; label: string }> = [
  { value: "ADMIN", label: t("common.administrator") },
  { value: "EMPLOYEE", label: t("common.operator") },
];

export function OwnershipTransferModal({ onClose }: { onClose: () => void }) {
  // Владелец и кандидаты приходят с сервера отдельным запросом: список
  // сотрудников теперь постраничный, и нужных людей может не быть на открытой
  // странице. Роль отбирает сервер, действующих — фильтр ниже.
  const [owner, setOwner] = useState<Employee | null>(null);
  const [candidates, setCandidates] = useState<Employee[]>([]);
  const [targetId, setTargetId] = useState<number | null>(null);
  // Поиск по кандидатам появляется, только если администраторов больше, чем
  // вернула страница: у обычной команды выбор остаётся простым списком.
  const [query, setQuery] = useState("");
  const [hasMore, setHasMore] = useState(false);
  const settledQuery = useDebounced(query);
  const [previousOwnerRole, setPreviousOwnerRole] = useState<Extract<Role, "ADMIN" | "EMPLOYEE">>("ADMIN");

  const [confirmed, setConfirmed] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void Promise.all([fetchOwner(), fetchOwnershipCandidates(settledQuery)])
      .then(([owners, admins]) => {
        if (!active) return;
        const activeAdmins = admins.items.filter((employee) => employee.isActive && !employee.isBlocked);
        setOwner(owners.items[0] ?? null);
        setCandidates(activeAdmins);
        setHasMore(admins.total > admins.items.length);
        setTargetId((current) => (
          activeAdmins.some((employee) => employee.id === current) ? current : activeAdmins[0]?.id ?? null
        ));
      })
      .catch(() => {
        if (active) setError(t("admin.could_not_load_candidates"));
      });
    return () => {
      active = false;
    };
  }, [settledQuery]);

  if (!owner) return null;
  const target = candidates.find((employee) => employee.id === targetId) ?? null;

  async function transfer() {
    if (!confirmed || !target || sending) return;
    setSending(true);
    setError("");
    try {
      await api(`/api/v1/employees/${target.id}/transfer-ownership/`, {
        method: "POST",
        body: JSON.stringify({ previousOwnerRole }),
      });
      window.location.reload();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("admin.ownership_transfer_failed"));
      setSending(false);
    }
  }

  return (
    <div className="employee-dialog-scrim">
      <section className="employee-transfer-dialog" role="dialog" aria-label={t("admin.ownership_transfer")}>
        <header>
          <i><Icon name="transfer" size={21} strokeWidth={1.9} /></i>
          <div>
            <h2>{t("admin.ownership_transfer")}</h2>
            <p>{t("admin.atomic_operation_organization_keeps_exactly")}</p>
          </div>
        </header>

        <div className="employee-transfer-body">
          {(hasMore || query) && (
            <SearchInput
              className="employee-transfer-search"
              placeholder={t("admin.name_email_or_position")}
              value={query}
              onChange={setQuery}
            />
          )}
          {candidates.length === 0 ? (
            <p className="employee-create-note">{t("admin.there_no_active_administrators_transfer")}</p>
          ) : (
            <>
              <label className="employee-field is-single">
                <span>{t("admin.new_owner_administrators_only")}</span>
                <span className="employee-transfer-select">
                  <select value={targetId === null ? "" : String(targetId)} onChange={(event) => setTargetId(Number(event.target.value))}>
                    {candidates.map((employee) => (
                      <option value={employee.id} key={employee.id}>
                        {employee.fullName || employee.email} · {roleBadge(employee.role).text} · {employee.positionTitle}
                      </option>
                    ))}
                  </select>
                  <Icon name="chevron" size={14} strokeWidth={1.8} />
                </span>
                <small className="employee-transfer-note">{t("admin.list_holds_active_administrators_only")}</small>
              </label>

              <div className="employee-transfer-pair">
                <div>
                  <Avatar employee={owner} background={employeeAvatarColor(owner)} />
                  <span>
                    <strong>{owner.fullName || owner.email}</strong>
                    <small>{t("common.owner")}</small>
                  </span>
                </div>
                <Icon name="arrow" size={20} strokeWidth={1.8} />
                <div>
                  {target && <Avatar employee={target} background={employeeAvatarColor(target)} />}
                  <span>
                    <strong>{target?.fullName || target?.email}</strong>
                    <small className="is-accent">{t("admin.owner")}</small>
                  </span>
                </div>
              </div>

              <div className="employee-transfer-role">
                <span>{t("admin.former_owner_s_new_role")}</span>
                <div>
                  {PREVIOUS_ROLES.map((option) => (
                    <button
                      className={`employee-transfer-role-option ${previousOwnerRole === option.value ? "is-on" : ""}`}
                      type="button"
                      onClick={() => setPreviousOwnerRole(option.value)}
                      key={option.value}
                    >
                      <i>{previousOwnerRole === option.value && <span />}</i>
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="employee-password-warning">
                <Icon name="warning" size={17} strokeWidth={1.9} />
                <p>{t("admin.new_owner_gains_full_access")}</p>
              </div>

              <button className="employee-transfer-confirm" type="button" aria-pressed={confirmed} onClick={() => setConfirmed((value) => !value)}>
                <i>{confirmed && <Icon name="check" size={12} strokeWidth={3} />}</i>
                <span>{t("admin.i_understand_consequences_confirm_transfer")}</span>
              </button>

              {error && <div className="employees-error"><Icon name="alert" size={16} strokeWidth={1.8} />{error}</div>}
            </>
          )}
        </div>

        <footer>
          <button className="secondary-button" type="button" onClick={onClose}>{t("common.cancel")}</button>
          <button className="employee-transfer-submit" type="button" disabled={!confirmed || !target || sending} onClick={() => void transfer()}>
            {sending ? t("admin.transferring") : t("admin.transfer_ownership")}
          </button>
        </footer>
      </section>
    </div>
  );
}
