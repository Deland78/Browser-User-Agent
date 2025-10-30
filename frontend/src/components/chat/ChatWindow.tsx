/**
 * ChatWindow - Main container for the browser automation chat interface
 *
 * Per US1-009: Container component for chat UI
 * Per FR-001: Chat interface for browser automation
 * Per FR-007: Conversation history
 * Per FR-017: Message persistence
 */

import { useCallback, useState } from "react";
import { nanoid } from "nanoid";
import { useEnvironment } from "../../hooks/useEnvironment";
import type { ChatMessage } from "../../types/chat";
import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";
import styles from "./ChatWindow.module.css";

const WELCOME_MESSAGE: ChatMessage = {
  id: "welcome",
  sender: "agent",
  content:
    "Hi! I'm your browser automation agent. I can help you navigate websites, click elements, fill forms, and extract information. Try commands like:\n• Go to example.com\n• Click the login button\n• Type 'hello' in the search box",
  timestamp: new Date().toISOString(),
  status: "sent",
};

export function ChatWindow() {
  const environment = useEnvironment();
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [isProcessing, setIsProcessing] = useState(false);

  /**
   * Handle sending a new message
   * Per FR-001: Accept user commands
   * Per FR-012: Show progress updates
   */
  const handleSendMessage = useCallback(
    (content: string) => {
      const trimmed = content.trim();
      if (!trimmed) {
        return;
      }

      // Create user message
      const userMessage: ChatMessage = {
        id: nanoid(),
        sender: "user",
        content: trimmed,
        timestamp: new Date().toISOString(),
        status: "pending",
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsProcessing(true);

      // TODO: US1-011 - Wire up to backend API
      // For now, show placeholder response
      setTimeout(() => {
        const agentMessage: ChatMessage = {
          id: nanoid(),
          sender: "agent",
          content:
            "I received your command! Once I'm connected to the backend (US1-010, US1-011), I'll execute browser actions and show you the results here.",
          timestamp: new Date().toISOString(),
          status: "sent",
        };

        // Update user message status
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === userMessage.id ? { ...msg, status: "sent" } : msg
          )
        );

        // Add agent response
        setMessages((prev) => [...prev, agentMessage]);
        setIsProcessing(false);
      }, 800);
    },
    []
  );

  return (
    <div className={styles.chatWindow} role="region" aria-label="Browser automation chat">
      {/* Environment banner for development */}
      {environment.environment === "development" && (
        <div className={styles.environmentBanner} role="status">
          <span>Mode: {environment.environment}</span>
          <span>API: {environment.apiUrl}</span>
        </div>
      )}

      {/* Message history */}
      <MessageList messages={messages} isProcessing={isProcessing} />

      {/* Message input */}
      <MessageInput onSend={handleSendMessage} disabled={isProcessing} />
    </div>
  );
}
