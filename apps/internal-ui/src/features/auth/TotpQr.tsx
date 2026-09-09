import { createQrMatrix } from "./qr";
import { t } from "../../i18n";

export function TotpQr({ value }: { value: string }) {
  const qr = createQrMatrix(value);
  return (
    <div className="auth-qr-shell">
      <div className="auth-qr-grid" style={{ gridTemplateColumns: `repeat(${qr.size}, 1fr)` }} aria-label={t("admin.qr_code_setting_up_totp")}>
        {qr.modules.map((active, index) => <span className={active ? "active" : ""} key={index} />)}
      </div>
    </div>
  );
}
