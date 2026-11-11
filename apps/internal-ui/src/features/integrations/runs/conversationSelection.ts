/** A selected form belongs to one visit to a conversation and one opening. */
export type ConversationSelectionContext = { conversationId: number | null };
export type ConversationSelectionToken = { context: ConversationSelectionContext; sequence: number };

export function createConversationSelection(conversationId: number | null) {
  let context: ConversationSelectionContext = { conversationId };
  let sequence = 0;
  return {
    enter(next: number | null) {
      if (context.conversationId !== next) { context = { conversationId: next }; sequence++; }
      return context;
    },
    begin(expected: ConversationSelectionContext): ConversationSelectionToken | null {
      if (expected !== context || context.conversationId === null) return null;
      return { context, sequence: ++sequence };
    },
    isCurrent(token: ConversationSelectionToken) {
      return token.context === context && token.sequence === sequence;
    },
    isContext(expected: ConversationSelectionContext) { return context === expected; },
    close(expected: ConversationSelectionContext) { if (expected === context) sequence++; },
  };
}
