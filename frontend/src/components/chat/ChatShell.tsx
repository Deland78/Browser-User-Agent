import { useCallback, useState } from "react";
import { nanoid } from "nanoid";
import { useEnvironment } from "../../hooks/useEnvironment";
import type { ChatMessage } from "../../types/chat";
import styles from "./ChatShell.module.css";
import { MessageList } from "./MessageList";
import { MessageComposer } from "./MessageComposer";

const welcomeMessage: ChatMessage = {
  id: "welcome",
  sender: "agent",
  content:
    "Hi there! I'm ready to interpret your browser commands. Try asking me to navigate to a URL or extract information.",
  timestamp: new Date().toISOString(),
};

export function ChatShell() {
  const environment = useEnvironment();
  const [messages, setMessages] = useState<ChatMessage[]>([welcomeMessage]);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSend = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) {
        return;
      }

      const userMessage: ChatMessage = {
        id: nanoid(),
        sender: "user",
        content: trimmed,
        timestamp: new Date().toISOString(),
        status: "pending",
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsProcessing(true);

      // Placeholder implementation until the real backend wiring exists.
      setTimeout(() => {
        const agentMessage: ChatMessage = {
          id: nanoid(),
          sender: "agent",
          content:
            "I'm not connected to the backend yet, but once I am I'll execute your request and report back here.",
          timestamp: new Date().toISOString(),
          status: "sent",
        };

        setMessages((prev) =>
          prev.map((message) =>
            message.id === userMessage.id ? { ...message, status: "sent" } : message,
          ),
        );
        setMessages((prev) => [...prev, agentMessage]);
        setIsProcessing(false);
      }, 800);
    },
    [setMessages],
  );

  return (
    <section className={styles.chatShell} aria-label="Browser automation chat">
      <div className={styles.environmentBanner}>
        <span>Mode: {environment.environment}</span>
        <span>API: {environment.apiUrl}</span>
      </div>
      <MessageList messages={messages} isProcessing={isProcessing} />
      <MessageComposer onSend={handleSend} disabled={isProcessing} />
    </section>
  );
}

