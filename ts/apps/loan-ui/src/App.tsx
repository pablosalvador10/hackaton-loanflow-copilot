/**
 * App root — single-page Loan Origination chatbot with layout wrapper.
 * Only one route: / (ChatPage).
 */

import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ConversationProvider } from "@/hooks/use-conversation";
import { AppLayout } from "@/components/layout/app-layout";
import { ChatPage } from "@/components/chat/chat-page";

export default function App() {
  return (
    <BrowserRouter>
      <ConversationProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<ChatPage />} />
          </Route>
        </Routes>
      </ConversationProvider>
    </BrowserRouter>
  );
}
