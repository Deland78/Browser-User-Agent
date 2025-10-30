/**
 * MessageBubble component for rendering individual chat messages
 *
 * Per US1-009: Individual message rendering component
 * Per FR-001: Chat interface display
 * Per FR-008: Human-readable confirmation messages
 * Per FR-009: Clear error messages
 */

import clsx from "clsx";
import { ExclamationTriangleIcon, CheckCircledIcon } from "@radix-ui/react-icons";
import type { ChatMessage } from "../../types/chat";
import styles from "./MessageBubble.module.css";

export type MessageBubbleProps = {
  message: ChatMessage;
};

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.sender === "user";
  const isError = message.status === "error";
  const isSuccess = message.status === "sent" || message.status === "delivered";
  const isPending = message.status === "pending";

  // Format timestamp
  const formattedTime = new Date(message.timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div
      className={clsx(styles.bubble, {
        [styles.userBubble]: isUser,
        [styles.agentBubble]: !isUser,
        [styles.pending]: isPending,
        [styles.error]: isError,
      })}
      role="article"
      aria-label={`Message from ${isUser ? "you" : "agent"} at ${formattedTime}`}
    >
      <div className={styles.header}>
        <span className={styles.sender} aria-label="Sender">
          {isUser ? "You" : "Agent"}
        </span>
        <span className={styles.timestamp} aria-label="Time">
          {formattedTime}
        </span>
      </div>

      <div className={styles.content}>
        {/* Status indicator icons */}
        {isError && (
          <ExclamationTriangleIcon
            className={styles.errorIcon}
            aria-label="Error"
            role="img"
          />
        )}
        {isSuccess && !isUser && (
          <CheckCircledIcon
            className={styles.successIcon}
            aria-label="Success"
            role="img"
          />
        )}

        {/* Message content */}
        <p className={styles.text}>{message.content}</p>

        {/* Metadata display (if present) */}
        {message.metadata && Object.keys(message.metadata).length > 0 && (
          <div className={styles.metadata} aria-label="Additional information">
            {typeof message.metadata.confidence === "number" && (
              <span className={styles.confidence}>
                Confidence: {Math.round(message.metadata.confidence * 100)}%
              </span>
            )}
            {typeof message.metadata.duration_ms === "number" && (
              <span className={styles.duration}>
                Took {Math.round(message.metadata.duration_ms)}ms
              </span>
            )}
          </div>
        )}

        {/* Loading indicator for processing state */}
        {isPending && (
          <div className={styles.loadingIndicator} aria-live="polite" aria-busy="true">
            <span className={styles.dot} />
            <span className={styles.dot} />
            <span className={styles.dot} />
          </div>
        )}
      </div>
    </div>
  );
}
