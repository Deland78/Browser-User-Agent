export type ChatSender = "user" | "agent" | "system";

export interface ChatMessage {
  id: string;
  sender: ChatSender;
  content: string;
  timestamp: string;
  status?: "pending" | "sent" | "error" | "delivered";
  metadata?: Record<string, unknown>;
}

