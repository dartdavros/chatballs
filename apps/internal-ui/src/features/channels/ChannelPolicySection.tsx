import { KeyValue, SwitchButton } from "../../shared/form-controls";
import { Icon } from "../../shared/icons";
import { POLICY_FLAGS, POLICY_LABELS, PRESET_LABELS, flagLock, presetOf } from "./model";
import type { Channel, PolicyFlag } from "./types";

/**
 * Пять флагов с однострочным пояснением следствия каждого (SPEC-HUB-0027 §11.2).
 *
 * Недоступный при текущем продукте флаг показан выключенным и заблокированным
 * с причиной и способом её устранить — он не игнорируется молча при сохранении.
 */
export function ChannelPolicySection({
  policy,
  hasProduct,
  productName,
  departmentName,
  editing,
  canManage,
  busy,
  onToggle,
}: {
  policy: Channel["policy"];
  hasProduct: boolean;
  productName: string;
  departmentName: string;
  editing: boolean;
  canManage: boolean;
  busy: boolean;
  onToggle: (flag: PolicyFlag, value: boolean) => void;
}) {
  const preset = PRESET_LABELS[presetOf(policy)];

  if (hasProduct) {
    return (
      <section className="channel-card-section channel-policy-section">
        <header>
          <h3>Политика</h3>
          <span>Пресет: {preset}</span>
        </header>
        <PolicyRows
          policy={policy}
          hasProduct
          editing={editing}
          canManage={canManage}
          busy={busy}
          switchFirst={false}
          onToggle={onToggle}
        />
      </section>
    );
  }

  return (
    <section className="channel-policy-scene" aria-label="Политика">
      <div className="channel-policy-flags-card">
        <div className="channel-policy-eyebrow">Политика</div>
        <PolicyRows
          policy={policy}
          hasProduct={false}
          editing={editing}
          canManage={canManage}
          busy={busy}
          switchFirst
          onToggle={onToggle}
        />
      </div>
      <aside className="channel-policy-context">
        <div className="channel-card-aside">
          <h4>Контекст политики</h4>
          <KeyValue label="Продукт" value={productName} />
          <KeyValue label="Отдел" value={departmentName} />
          <KeyValue label="Пресет" value={preset} />
        </div>
        <p className="channel-policy-note">
          Настройки сохраняются целиком: если хотя бы одна недоступна, не сохранится ни одна.
          Чтобы включить коммерческие настройки, сначала назначьте продукт в секции «Назначение».
        </p>
      </aside>
    </section>
  );
}

function PolicyRows({
  policy,
  hasProduct,
  editing,
  canManage,
  busy,
  switchFirst,
  onToggle,
}: {
  policy: Channel["policy"];
  hasProduct: boolean;
  editing: boolean;
  canManage: boolean;
  busy: boolean;
  switchFirst: boolean;
  onToggle: (flag: PolicyFlag, value: boolean) => void;
}) {
  return (
    <div className="channel-policy-flags">
      {POLICY_FLAGS.map((flag) => {
        const lock = flagLock(flag, policy, hasProduct);
        const emphasized = lock !== null && flag === "allowCheckoutActions";
        const control = (
          <SwitchButton
            className="ui-switch"
            checked={policy[flag]}
            disabled={!editing || !canManage || lock !== null || busy}
            label={POLICY_LABELS[flag].title}
            onClick={() => onToggle(flag, !policy[flag])}
          />
        );
        return (
          <div className={`channel-policy-row ${lock ? "is-locked" : ""} ${emphasized ? "is-emphasized" : ""}`.trim()} key={flag}>
            {switchFirst && control}
            <div className="channel-policy-text">
              <div className="channel-policy-title">
                {POLICY_LABELS[flag].title}
                {lock && <span className="channel-lock-badge"><Icon name="lock" size={11} />Недоступно</span>}
              </div>
              <p>{lock ? `${lock.reason}. ${lock.fix}` : POLICY_LABELS[flag].hint}</p>
            </div>
            {!switchFirst && control}
          </div>
        );
      })}
    </div>
  );
}
