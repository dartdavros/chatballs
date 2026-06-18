import { Icon } from "../../../../shared/icons";
import { ContextSection } from "./ContextSection";

export function ProductContext() {
  return (
    <div className="sales-product-context">
      <div className="sales-product-head"><span><Icon name="box" size={20} /></span><div><strong>FirePage</strong><small>Конструктор лендингов · активен</small></div></div>
      <ContextSection title="ПОДХОДЯЩИЕ OFFER">
        <div className="sales-offer active"><div><strong>Business</strong><em>AI может предлагать</em></div><p><b>₽2 490</b><span>/ мес · помесячно</span></p><small>До 10 пользователей · общие проекты · amoCRM-интеграция · приоритетная поддержка.</small></div>
        <div className="sales-offer"><div><strong>Pro</strong><em>для одного</em></div><p><b>₽990</b><span>/ мес</span></p><small>1 пользователь · все шаблоны · базовая поддержка.</small></div>
      </ContextSection>
    </div>
  );
}
