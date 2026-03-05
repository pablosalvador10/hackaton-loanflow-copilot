/**
 * Chat page — the single-page loan origination chat interface.
 * Composes the message list + input + document upload into a
 * full-height conversational view.
 */

import { useCallback } from "react";
import { ChatMessageList } from "@/components/chat/chat-message-list";
import { ChatInput } from "@/components/chat/chat-input";
import { ToastContainer } from "@/components/chat/toast";
import { useConversation } from "@/hooks/use-conversation";
import type { UploadedDocument } from "@/types";

export function ChatPage() {
  const {
    messages,
    isLoading,
    sendMessage,
    toasts,
    dismissToast,
    pendingDocument,
    setPendingDocument,
  } = useConversation();

  const handleFileSelect = useCallback(
    (file: File) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        const b64 = result.includes(",") ? result.split(",")[1] : result;

        const doc: UploadedDocument = {
          documentId: crypto.randomUUID(),
          documentType: "drivers_license", // default; agent will infer
          fileName: file.name,
          fileSize: file.size,
          base64Content: b64,
        };

        setPendingDocument(doc);
      };
      reader.readAsDataURL(file);
    },
    [setPendingDocument]
  );

  return (
    <div className="flex flex-col h-full">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      {/* Messages area — fills available space, scrolls internally */}
      <ChatMessageList
        messages={messages}
        isLoading={isLoading}
        onPromptClick={sendMessage}
      />

      {/* Pending document indicator */}
      {pendingDocument && (
        <div className="border-t border-foreground/[0.04] bg-primary/[0.02]">
          <div className="max-w-3xl mx-auto px-4 py-2 flex items-center justify-between">
            <span className="text-xs text-primary/70">
              📎 {pendingDocument.fileName} attached — send a message to process it
            </span>
            <button
              onClick={() => setPendingDocument(null)}
              className="text-xs text-foreground/40 hover:text-foreground/60 transition-colors"
            >
              Remove
            </button>
          </div>
        </div>
      )}

      {/* Input area — fixed at bottom */}
      <div className="border-t border-foreground/[0.04] bg-background/80 backdrop-blur-md">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <ChatInput
            onSend={sendMessage}
            onFileSelect={handleFileSelect}
            disabled={isLoading}
            hasPendingDocument={!!pendingDocument}
          />
          <p className="text-[10px] text-foreground/20 text-center mt-2.5 select-none">
            AI-generated content may contain errors. Verify all financial details before proceeding.
          </p>
        </div>
      </div>
    </div>
  );
}
