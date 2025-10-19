import clsx from "clsx";
import { useMemo } from "react";
import type { ChatMessage } from "../../types/chat";
import styles from "./MessageList.module.css";

type MessageListProps = {
  messages: ChatMessage[];
  isProcessing: boolean;
  summary: {
    totalMessages: number;
    lastSender: string;
  };
};

export function MessageList({ messages, isProcessing, summary }: MessageListProps) {
  const ariaLabel = useMemo(
    () => `Conversation, ${summary.totalMessages} messages, last from ${summary.lastSender}`,
    [summary.totalMessages, summary.lastSender],
  );

  return (
    <div className={styles.container}>
      <div className={styles.meta}>
        <span aria-live="polite">{ariaLabel}</span>
        {isProcessing ? <span className={styles.typing}>Agent is thinking...</span> : null}
      </div>
      <ol className={styles.list} aria-label={ariaLabel} role="log" aria-live="polite">
        {messages.map((message) => (
          <li
            key={message.id}
            className={clsx(styles.message, {
              [styles.userMessage]: message.sender === "user",
              [styles.pending]: message.status === "pending",
            })}
          >
            <span className={styles.sender}>{message.sender === "user" ? "You" : "Agent"}</span>
            <p>{message.content}</p>
            <span className={styles.timestamp}>
              {new Date(message.timestamp).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

