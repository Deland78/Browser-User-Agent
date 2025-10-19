import { FormEvent, useState } from "react";
import styles from "./MessageComposer.module.css";

type MessageComposerProps = {
  onSend: (input: string) => void;
  disabled?: boolean;
};

export function MessageComposer({ onSend, disabled = false }: MessageComposerProps) {
  const [message, setMessage] = useState("");

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSend(message);
    setMessage("");
  };

  return (
    <form className={styles.composer} onSubmit={handleSubmit} aria-label="Send a message">
      <label className={styles.label} htmlFor="chat-input">
        Message
      </label>
      <textarea
        id="chat-input"
        name="chat-input"
        aria-describedby="chat-helper-text"
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        placeholder='Example: "Navigate to example.com and list the first 3 headlines."'
        rows={3}
        required
      />
      <div className={styles.composerControls}>
        <span id="chat-helper-text" className={styles.helperText}>
          Press Enter to send, Shift+Enter for a new line.
        </span>
        <button type="submit" disabled={disabled || !message.trim()} aria-disabled={disabled}>
          {disabled ? "Working…" : "Send"}
        </button>
      </div>
    </form>
  );
}

