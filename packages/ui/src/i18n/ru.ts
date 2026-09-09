// Словарь общих компонентов: экран звонка и загрузка.
//
// У пакета свой словарь, а не общий с рабочим местом: пакет не знает, кто его
// подключил, — и виджет клиента, и рабочее место сотрудника берут отсюда одни
// и те же кнопки звонка. Язык при этом общий: его держит @chatballs/shared.

import type { Message } from "@chatballs/shared";

export const ru = {
  "call.accept": "Принять",
  "call.audio_call": "Аудиозвонок",
  "call.audio_not_supported": "Аудиозвонки не поддерживаются",
  "call.call_again": "Позвонить снова",
  "call.call_cancelled": "Звонок отменён",
  "call.call_declined": "Звонок отклонён",
  "call.call_ended": "Звонок завершён",
  "call.calling": "Вызываем…",
  "call.camera": "Камера",
  "call.camera_off": "Камера выключена",
  "call.cancel": "Отмена",
  "call.cancel_call": "Отменить",
  "call.close": "Закрыть",
  "call.conversation_ended": "Разговор завершён.",
  "call.connecting": "Соединяем",
  "call.connecting_status": "Соединение",
  "call.check_connection": "Проверьте интернет-соединение и попробуйте снова.",
  "call.declined_by": "{name} отклонил(а) вызов.",
  "call.decline": "Отклонить",
  "call.duration": "Длительность {duration}.",
  "call.end": "Завершить",
  "call.enter_fullscreen": "Полный экран",
  "call.establishing": "Устанавливаем защищённое соединение…",
  "call.exit_fullscreen": "Выйти из полноэкранного режима",
  "call.incoming": "Входящий звонок",
  "call.invitation_cancelled": "Приглашение отменено.",
  "call.join": "Присоединиться",
  "call.joining": "Подключение…",
  "call.link_unsupported_browser": "Обновите браузер или откройте ссылку в Chrome, Safari или Edge.",
  "call.mic": "Микрофон",
  "call.mic_off": "Ваш микрофон выключен",
  "call.missed": "Пропущенный звонок",
  "call.no_mic_access": "Нет доступа к микрофону",
  "call.nobody_answered": "Никто не ответил вовремя. Попробуйте позвонить снова.",
  "call.outgoing": "Исходящий звонок",
  "call.peer_camera_off": "Камера собеседника выключена",
  "call.reconnecting": "Переподключение",
  "call.reconnecting_inline": "Связь прервана · восстанавливаем соединение…",
  "call.reconnecting_caption": "Восстанавливаем соединение…",
  "call.reconnecting_title": "Связь прервана",
  "call.retry": "Повторить",
  "call.retry_check": "Повторить проверку",
  "call.speak": "Говорите",
  "call.speaker": "Динамик",
  "call.unanswered_by": "{name} не ответил(а) на вызов.",
  "call.unable_to_connect": "Не удалось соединиться",
  "call.wait_timed_out": "Время ожидания истекло",
  "call.you": "Вы",
  "call.you_initials": "ВЫ",
  "call.allow_mic": "Разрешите доступ к микрофону в настройках браузера и повторите.",
  "common.loading": "Загрузка",
} satisfies Record<string, Message>;

export type UiMessageKey = keyof typeof ru;
