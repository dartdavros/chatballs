import { createContext, useContext } from "react";
import type { useConversationRunsState } from "./useConversationRunsState";

export const ConversationRunsContext = createContext<ReturnType<typeof useConversationRunsState> | null>(null);
export const useConversationRuns = () => useContext(ConversationRunsContext);
