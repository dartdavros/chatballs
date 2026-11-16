export const clientCases = [
  {
    id: 'S60', titleRu: 'Клиент: требуется новая редакция согласия', titleEn: 'Customer: a new consent revision is required',
    descriptionRu: 'Проект новой редакции v2 в текущем виджете. Прежнее согласие не считается принятием этой редакции; внешний экспорт заблокирован до подтверждения. Юридическая достаточность текста и получатель не проверены.',
    descriptionEn: 'Proposed revision v2 in the current widget. Earlier consent does not accept this revision; external export is blocked until confirmation. Legal sufficiency and the recipient have not been verified.',
  },
  {
    id: 'S61', titleRu: 'Клиент: новая редакция в форме перед чатом', titleEn: 'Customer: new revision in the pre-chat form',
    descriptionRu: 'Та же предлагаемая редакция в существующей форме с именем и email. Обязательное имя не заполнено: начало чата недоступно. Отправка полей и принятие согласия не выполняются.',
    descriptionEn: 'The same proposed revision in the existing name and email form. The required name is empty, so starting the chat is unavailable. No fields are submitted and no consent is accepted.',
  },
  {
    id: 'S62', titleRu: 'Клиент: актуальная редакция принята', titleEn: 'Customer: the current revision is accepted',
    descriptionRu: 'Условное состояние после серверного подтверждения актуальной редакции: открыт штатный композер. Это не выполненное согласие; сам факт принятия не подтверждает настройки, полномочия или готовность внешнего исполнения.',
    descriptionEn: 'Conditional state after server confirmation of the current revision: the standard composer is open. No consent was actually accepted; acceptance alone does not prove external configuration, authorization or readiness.',
  },
  {
    id: 'S63', titleRu: 'Клиент: голосовое сохранено, ожидается сотрудник', titleEn: 'Customer: voice message retained, waiting for an employee',
    descriptionRu: 'Единый клиентский вид при отсутствии или сбое STT: штатный плеер голосового и ожидание сотрудника. Расшифровка и внешний ответ не придуманы. Волна и 12 секунд — иллюстрация документа; аудиофайла и воспроизведения нет.',
    descriptionEn: 'The common customer view when STT is missing or fails: the standard voice player and employee waiting notice. No transcript or external reply is invented. The waveform and 12 seconds are document illustrations; there is no audio file or playback.',
  },
] as const;

export type ClientVariant = typeof clientCases[number]['id'];
