import { useState } from "react";
import { WelcomeScreen } from "./components/WelcomeScreen";
import { ChatScreen } from "./components/ChatScreen";

export default function App() {
  const [started, setStarted] = useState(false);
  return started ? <ChatScreen /> : <WelcomeScreen onStart={() => setStarted(true)} />;
}
