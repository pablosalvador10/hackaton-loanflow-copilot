/**
 * App root — LOH AI Lending Copilot.
 * Two screens: Welcome → Chat (copilot conversation flow).
 */

import { CopilotProvider, useCopilot } from "@/hooks/use-copilot";
import { WelcomeScreen } from "@/components/copilot/welcome-screen";
import { ChatScreen } from "@/components/copilot/chat-screen";

function AppInner() {
  const { messages } = useCopilot();
  // Show chat screen once the copilot has started (messages exist)
  return messages.length > 0 ? <ChatScreen /> : <WelcomeScreen />;
}

export default function App() {
  return (
    <CopilotProvider>
      <AppInner />
    </CopilotProvider>
  );
}
