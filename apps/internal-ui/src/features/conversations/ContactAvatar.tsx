import { useState } from "react";

/**
 * Аватар контакта: фото (если провайдер отдал avatar_url) с fallback на круг
 * с инициалами. Если изображение не загрузилось — показываем инициалы.
 *
 * className задаёт размер/радиус — компонент переиспользуется в списке
 * диалогов, шапке треда и у сообщений. Фон инициалов передаётся отдельно,
 * т.к. он стабилен по id контакта.
 */
export function ContactAvatar({
  avatarUrl,
  initials,
  background,
  className,
}: {
  avatarUrl?: string;
  initials: string;
  background: string;
  className: string;
}) {
  const [failed, setFailed] = useState(false);
  if (avatarUrl && !failed) {
    return <img className={className} src={avatarUrl} alt="" onError={() => setFailed(true)} />;
  }
  return (
    <span className={className} style={{ background }}>
      {initials}
    </span>
  );
}
