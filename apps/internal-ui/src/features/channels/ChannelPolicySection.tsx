import { POLICY_FLAGS, POLICY_LABELS, PRESET_LABELS, flagLock, presetOf } from "./model";
import type { Channel, PolicyFlag } from "./types";

/**
 * Пять флагов с однострочным пояснением следствия каждого (SPEC-HUB-0027 §11.2).
 *
 * Флаг, запрещённый инвариантом при текущем продукте, показан выключенным и
 * заблокированным с причиной — он не игнорируется молча при сохранении.
 */
export function ChannelPolicySection({
  channel,
  canManage,
  onToggle,
}: {
  channel: Channel;
  canManage: boolean;
  onToggle: (flag: PolicyFlag, value: boolean) => void;
}) {
  const hasProduct = channel.product !== null;
  return (
    <section className="channel-card-section channel-policy">
      <header>
        <h3>Политика</h3>
        <span>Пресет: {PRESET_LABELS[presetOf(channel.policy)]}</span>
      </header>
      {POLICY_FLAGS.map((flag) => {
        const lock = flagLock(flag, channel.policy, hasProduct);
        const checked = channel.policy[flag];
        const disabled = !canManage || lock !== null;
        return (
          <div className={`channel-policy-row ${lock ? "is-locked" : ""}`} key={flag}>
            <label className="channel-switch">
              <input
                type="checkbox"
                checked={checked}
                disabled={disabled}
                onChange={(event) => onToggle(flag, event.target.checked)}
              />
              <span />
            </label>
            <div className="channel-policy-text">
              <div className="channel-policy-title">
                {POLICY_LABELS[flag].title}
                {lock && <span className="channel-lock-badge">Запрещено инвариантом</span>}
              </div>
              <p>
                {lock ? (
                  <>
                    {lock.reason} <b>(инвариант {lock.rule})</b>. {lock.fix}
                  </>
                ) : (
                  POLICY_LABELS[flag].hint
                )}
              </p>
            </div>
          </div>
        );
      })}
      <p className="channel-policy-note">
        Инварианты проверяются по итоговому состоянию: частичное сохранение запрещено.
      </p>
    </section>
  );
}
