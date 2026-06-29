import { useState } from "react";

import type { TestChannel } from "./model";
import { TestChatDiagnostics } from "./TestChatDiagnostics";
import { TestChatSidebar } from "./TestChatSidebar";
import { TestConversation } from "./TestConversation";

export function AiTestChatPage() {
  const [channel, setChannel] = useState<TestChannel>("MAX");
  const [scenario, setScenario] = useState("box");

  return (
    <div className="ai-test-chat-page">
      <TestChatSidebar channel={channel} scenario={scenario} setChannel={setChannel} setScenario={setScenario} />
      <TestConversation channel={channel} />
      <TestChatDiagnostics />
    </div>
  );
}
