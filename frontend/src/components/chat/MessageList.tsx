/**
 * MessageList - Displays conversation history with scrolling
 *
 * Per US1-009: Display message history
 * Per FR-007: Conversation history
 * Per FR-018: Scrollable message list
 * Per Decision 6: ARIA live region for accessibility
 */

import { useEffect, useRef, useMemo } from "react";
import type { ChatMessage } from "../../types/chat";
import { MessageBubble } from "./MessageBubble";
import styles from "./MessageList.module.css";

export type MessageListProps = {
  messages: ChatMessage[];
  isProcessing: boolean;
};

export function MessageList({ messages, isProcessing }: MessageListProps) {
  const listEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  // Per FR-018: Auto-scroll behavior
  useEffect(() => {
    if (listEndRef.current) {
      listEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages.length]);

  // Accessibility: Generate summary for screen readers
  const summary = useMemo(() => {
    const totalMessages = messages.length;
    const lastMessage = messages[messages.length - 1];
    const lastSender = lastMessage?.sender === "user" ? "you" : "agent";

    return `Conversation with ${totalMessages} ${totalMessages === 1 ? "message" : "messages"}, last from ${lastSender}`;
  }, [messages]);

  return (
    <div className={styles.container} ref={containerRef}>
      {/* Screen reader announcement for processing state */}
      {isProcessing && (
        <div className={styles.srOnly} role="status" aria-live="polite" aria-atomic="true">
          Agent is processing your message
        </div>
      )}

      {/* Visual processing indicator */}
      {isProcessing && (
        <div className={styles.processingIndicator} aria-hidden="true">
          <span className={styles.dot} />
          <span className={styles.dot} />
          <span className={styles.dot} />
          <span className={styles.indicatorText}>Agent is thinking...</span>
        </div>
      )}

      {/* Message list */}
      <div
        className={styles.messageList}
        role="log"
        aria-live="polite"
        aria-relevant="additions"
        aria-label={summary}
      >
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {/* Scroll anchor */}
        <div ref={listEndRef} className={styles.scrollAnchor} aria-hidden="true" />
      </div>
    </div>
  );
}
