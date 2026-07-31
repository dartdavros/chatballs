// Диспетчер звонка по типу (call.kind): VIDEO → видеозвонок (VideoCallOverlay,
// существующий путь), AUDIO → аудиозвонок (AudioCallOverlay, baseline
// «Аудиозвонок.dc.html»). Сам по себе ничего не рендерит — composition-only.

import { AudioCallOverlay } from "./AudioCallOverlay";
import { VideoCallOverlay } from "./VideoCallOverlay";
import type { ApiCall, CallAccess } from "./model";
import type { ConversationListItem } from "./types";

type Props = {
  open: boolean;
  dialog: ConversationListItem | null;
  call: ApiCall | null;
  requestedKind: ApiCall["kind"] | null;
  access: CallAccess | null;
  errorText: string;
  onCallChange: (call: ApiCall) => void;
  onCancel: () => void;
  onRetry: () => void;
  onClose: () => void;
};

export function CallOverlay(props: Props) {
  // Активный/существующий звонок возвращается из API с kind; пока запрос
  // выполняется, используем явно выбранный тип. Неизвестный kind не подменяем.
  const kind = props.call?.kind ?? props.requestedKind;
  if (kind === "VIDEO") return <VideoCallOverlay {...props} />;
  if (kind === "AUDIO") return <AudioCallOverlay {...props} />;
  return null;
}
