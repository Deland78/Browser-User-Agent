/**
 * MessageInput - User input component for sending commands
 *
 * Per US1-009: User input with send button
 * Per FR-001: Accept user commands
 * Per FR-013: Command cancellation support
 * Per Decision 6: Accessible form with clear labels
 */

import { FormEvent, useState, KeyboardEvent } from "react";
import { PaperPlaneIcon, Cross2Icon } from "@radix-ui/react-icons";
import styles from "./MessageInput.module.css";

export type MessageInputProps = {
  onSend: (content: string) => void;
  disabled?: boolean;
};

export function MessageInput({ onSend, disabled = false }: MessageInputProps) {
  const [message, setMessage] = useState("");

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmed = message.trim();
    if (!trimmed || disabled) {
      return;
    }

    onSend(trimmed);
    setMessage("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter to send, Shift+Enter for new line
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event as any);
    }
  };

  const handleClear = () => {
    setMessage("");
  };

  const isMessageEmpty = message.trim().length === 0;

  return (
    <form
      className={styles.messageInput}
      onSubmit={handleSubmit}
      aria-label="Send a browser automation command"
    >
      <div className={styles.inputContainer}>
        <label htmlFor="chat-input" className={styles.label}>
          Command
        </label>

        <textarea
          id="chat-input"
          name="chat-input"
          className={styles.textarea}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder='Try: "Go to example.com" or "Click the login button"'
          rows={2}
          disabled={disabled}
          aria-describedby="chat-help-text"
          aria-required="true"
        />

        <span id="chat-help-text" className={styles.helpText}>
          {disabled
            ? "Agent is processing..."
            : "Press Enter to send, Shift+Enter for new line"}
        </span>
      </div>

      <div className={styles.controls}>
        {/* Clear button */}
        {!isMessageEmpty && !disabled && (
          <button
            type="button"
            onClick={handleClear}
            className={styles.clearButton}
            aria-label="Clear message"
            title="Clear message"
          >
            <Cross2Icon aria-hidden="true" />
          </button>
        )}

        {/* Send button */}
        <button
          type="submit"
          className={styles.sendButton}
          disabled={disabled || isMessageEmpty}
          aria-disabled={disabled || isMessageEmpty}
          aria-label="Send command"
          title={disabled ? "Processing..." : "Send command"}
        >
          {disabled ? (
            <>
              <span className={styles.spinner} aria-hidden="true" />
              <span>Processing...</span>
            </>
          ) : (
            <>
              <PaperPlaneIcon aria-hidden="true" />
              <span>Send</span>
            </>
          )}
        </button>
      </div>
    </form>
  );
}
