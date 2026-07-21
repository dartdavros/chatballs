import { KeyValue, SwitchButton } from "../../shared/form-controls";
import { POLICY_FLAGS, POLICY_LABELS, PRESET_LABELS, flagLock, presetOf } from "./model";
import type { Channel, PolicyFlag } from "./types";

/**
 * Пять флагов с однострочным пояснением следствия каждого (SPEC-HUB-0027 §11.2).
 *
 * Недоступный при текущем продукте флаг показан выключенным и заблокированным
 * с причиной и способом её устранить — он не игнорируется молча при сохранении.
 */
export function ChannelPolicySection({
  channel,
  canManage,
  busy,
  onToggle,
  onAssignProduct,
}: {
  channel: Channel;
  canManage: boolean;
  busy: boolean;
  onToggle: (flag: PolicyFlag, value: boolean) => void;
  onAssignProduct: () => void;
}) {
  const hasProduct = channel.product !== null;

  return (
    <section className="channel-card-section">
      <header>
        <h3>Политика</h3>
        <span>Пресет: {PRESET_LABELS[presetOf(channel.policy)]}</span>
      </header>

      <div className="channel-policy-layout">
        <div className="channel-policy-flags">
          {POLICY_FLAGS.map((flag) => {
            const lock = flagLock(flag, channel.policy, hasProduct);
            return (
              <div className={`channel-policy-row ${lock ? "is-locked" : ""}`} key={flag}>
                <div className="channel-policy-text">
                  <div className="channel-policy-title">
                    {POLICY_LABELS[flag].title}
                    {lock && <span className="channel-lock-badge">Недоступно</span>}
                  </div>
                  <p>{lock ? `${lock.reason}. ${lock.fix}` : POLICY_LABELS[flag].hint}</p>
                  {lock?.needsProduct && canManage && (
                    <button className="link" type="button" onClick={onAssignProduct}>
                      Назначить продукт
                    </button>
                  )}
                </div>
                <SwitchButton
                  className="ui-switch"
                  checked={channel.policy[flag]}
                  disabled={!canManage || lock !== null || busy}
                  label={POLICY_LABELS[flag].title}
                  onClick={() => onToggle(flag, !channel.policy[flag])}
                />
              </div>
            );
          })}
        </div>

        <aside className="channel-policy-context">
          <div className="channel-card-aside">
            <h4>Контекст политики</h4>
            <KeyValue label="Продукт" value={channel.product?.name ?? "— непродуктовый"} />
            <KeyValue label="Отдел" value={channel.departmentName ?? "Без отдела"} />
            <KeyValue label="Пресет" value={PRESET_LABELS[presetOf(channel.policy)]} />
          </div>
          <p className="channel-policy-note">
            Настройки сохраняются целиком: если хотя бы одна недоступна, не сохранится ни одна.
            Чтобы включить коммерческие настройки, сначала назначьте продукт в секции «Назначение».
          </p>
        </aside>
      </div>
    </section>
  );
}
