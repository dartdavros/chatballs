import { t } from "../../../i18n";
import type { externalMessagesRu } from "../../../i18n/external-agent.ru";

type ExternalKey = keyof typeof externalMessagesRu extends `external.${infer Key}` ? Key : never;
export const et = (key: ExternalKey, values?: Parameters<typeof t>[1]) => t(`external.${key}`, values);
