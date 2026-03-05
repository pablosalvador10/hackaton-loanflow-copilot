/**
 * Chat page — the single-page VIN Insight chat interface.
 * Composes the message list + input into a full-height conversational view.
 * All state comes from the ConversationProvider context.
 */

import { ChatMessageList } from "@/components/chat/chat-message-list";
import { ChatInput } from "@/components/chat/chat-input";
import { ToastContainer } from "@/components/chat/toast";
import { useConversation } from "@/hooks/use-conversation";

export function ChatPage() {
  const {
    messages,
    isLoading,
    sendMessage,
    toasts,
    dismissToast,
  } = useConversation();

  return (
    <div className="flex flex-col h-full">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      {/* Messages area — fills available space, scrolls internally */}
      <ChatMessageList
        messages={messages}
        isLoading={isLoading}
        onPromptClick={sendMessage}
      />

      {/* Input area — fixed at bottom with subtle top border */}
      <div className="border-t border-foreground/[0.04] bg-background/80 backdrop-blur-md">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <ChatInput onSend={sendMessage} disabled={isLoading} />
          <p className="text-[10px] text-foreground/20 text-center mt-2.5 select-none">
            AI-generated reports may not always be accurate. Verify critical details.
          </p>
        </div>
      </div>
    </div>
  );
}
