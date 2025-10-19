import { ChatShell } from "./components/chat/ChatShell";
import styles from "./App.module.css";

function App() {
  return (
    <div className={styles.appShell}>
      <header className={styles.header}>
        <div>
          <h1>Browser Automation Agent</h1>
          <p>Conversational control of the web browser with confidence-aware automation.</p>
        </div>
      </header>
      <main className={styles.mainContent}>
        <ChatShell />
      </main>
    </div>
  );
}

export default App;

