import { createQrMatrix } from "./qr";

export function TotpQr({ value }: { value: string }) {
  const qr = createQrMatrix(value);
  return (
    <div className="auth-qr-shell">
      <div className="auth-qr-grid" style={{ gridTemplateColumns: `repeat(${qr.size}, 1fr)` }} aria-label="QR-код для подключения TOTP">
        {qr.modules.map((active, index) => <span className={active ? "active" : ""} key={index} />)}
      </div>
    </div>
  );
}
