import { agentBaseMessagesRu } from "./external-agent/agent-base.ru";
import { offMessagesRu } from "./external-agent/off.ru";
import { setupMessagesRu } from "./external-agent/setup.ru";
import { readyMessagesRu } from "./external-agent/ready.ru";
import { settingsMessagesRu } from "./external-agent/settings.ru";
import { policyMessagesRu } from "./external-agent/policy.ru";
import { casesMessagesRu } from "./external-agent/cases.ru";
import { feedbackMessagesRu } from "./external-agent/feedback.ru";
import { bindingMessagesRu } from "./external-agent/binding.ru";
import { helpMessagesRu } from "./external-agent/help.ru";
import { agentMessagesRu } from "./external-agent/agent.ru";
import { testMessagesRu } from "./external-agent/test.ru";
import { chatMessagesRu } from "./external-agent/chat.ru";

export const externalMessagesRu = {
  ...agentBaseMessagesRu,
  ...offMessagesRu,
  ...setupMessagesRu,
  ...readyMessagesRu,
  ...settingsMessagesRu,
  ...policyMessagesRu,
  ...casesMessagesRu,
  ...feedbackMessagesRu,
  ...bindingMessagesRu,
  ...helpMessagesRu,
  ...agentMessagesRu,
  ...testMessagesRu,
  ...chatMessagesRu,
};
