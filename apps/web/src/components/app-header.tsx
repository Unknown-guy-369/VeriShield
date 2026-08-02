import { ShieldCheck } from "lucide-react";
import styles from "./app-header.module.css";

export function AppHeader() {
  return (
    <header className={styles.header}>
      <a className={styles.brand} href="#main-content" aria-label="VeriShield AI home">
        <span className={styles.mark} aria-hidden="true">
          <ShieldCheck size={20} strokeWidth={1.8} />
        </span>
        <span>
          <strong>VeriShield AI</strong>
          <small>Verification workspace</small>
        </span>
      </a>
      <div className={styles.context}>
        <span className={styles.liveDot} aria-hidden="true" />
        Prototype intake
      </div>
    </header>
  );
}
