import { agentBaseMessagesEn } from "./external-agent/agent-base.en";
import { offMessagesEn } from "./external-agent/off.en";
import { setupMessagesEn } from "./external-agent/setup.en";
import { readyMessagesEn } from "./external-agent/ready.en";
import { settingsMessagesEn } from "./external-agent/settings.en";
import { policyMessagesEn } from "./external-agent/policy.en";
import { casesMessagesEn } from "./external-agent/cases.en";
import { feedbackMessagesEn } from "./external-agent/feedback.en";
import { bindingMessagesEn } from "./external-agent/binding.en";
import { helpMessagesEn } from "./external-agent/help.en";
import { agentMessagesEn } from "./external-agent/agent.en";
import { testMessagesEn } from "./external-agent/test.en";
import { chatMessagesEn } from "./external-agent/chat.en";

export const externalMessagesEn = {
  ...agentBaseMessagesEn,
  ...offMessagesEn,
  ...setupMessagesEn,
  ...readyMessagesEn,
  ...settingsMessagesEn,
  ...policyMessagesEn,
  ...casesMessagesEn,
  ...feedbackMessagesEn,
  ...bindingMessagesEn,
  ...helpMessagesEn,
  ...agentMessagesEn,
  ...testMessagesEn,
  ...chatMessagesEn,
};
