"use client";

import {
  Check,
  CheckCircle2,
  Clipboard,
  LoaderCircle,
  ServerCrash,
  WifiOff,
} from "lucide-react";
import { useState } from "react";
import type { AnalysisRecord } from "@/lib/analysis";
import { ApiClientError } from "@/lib/api";
import styles from "./request-receipt.module.css";

type RequestReceiptProps = {
  phase: "idle" | "submitting" | "success" | "error";
  record: AnalysisRecord | null;
  error: Error | null;
  liveUpdatesPaused: boolean;
};

function clampProgress(value: number) {
  return Math.min(100, Math.max(0, Math.round(value)));
}

export function RequestReceipt({
  phase,
  record,
  error,
  liveUpdatesPaused,
}: RequestReceiptProps) {
  const [copied, setCopied] = useState(false);

  if (phase === "idle") {
    return (
      <div className={styles.empty} aria-live="polite">
        <span className={styles.emptyIcon} aria-hidden="true">
          <CheckCircle2 size={18} />
        </span>
        <p>
          <strong>No analysis submitted yet</strong>
          Your request receipt and processing status will appear here.
        </p>
      </div>
    );
  }

  if (phase === "submitting") {
    return (
      <div className={styles.loading} aria-live="polite" aria-busy="true">
        <div className={styles.loadingTitle}>
          <LoaderCircle className={styles.spinner} size={18} aria-hidden="true" />
          <p>
            <strong>Sending content</strong>
            The intake API is validating and creating a traceable request.
          </p>
        </div>
        <div className={styles.indeterminate} aria-hidden="true">
          <span />
        </div>
      </div>
    );
  }

  if (phase === "error" && error) {
    const unavailable =
      error instanceof ApiClientError &&
      (error.code === "NETWORK" || error.code === "TIMEOUT");
    const Icon = unavailable ? WifiOff : ServerCrash;
    return (
      <div className={styles.error} role="status">
        <Icon size={19} aria-hidden="true" />
        <p>
          <strong>{unavailable ? "Analysis API unavailable" : "Request not accepted"}</strong>
          {error.message}
          <small>Your input is still in this browser and can be submitted again.</small>
        </p>
      </div>
    );
  }

  if (!record) return null;

  const progress = clampProgress(record.progress);
  return (
    <section className={styles.receipt} aria-labelledby="request-receipt-title">
      <div className={styles.receiptHeader}>
        <span className={styles.receiptCheck} aria-hidden="true">
          <Check size={17} />
        </span>
        <div>
          <h2 id="request-receipt-title">Request accepted</h2>
          <p>{liveUpdatesPaused ? "Live updates paused" : "Processing status is live"}</p>
        </div>
        <span className={styles.status}>{record.status.replaceAll("_", " ")}</span>
      </div>

      <div className={styles.progressLabel}>
        <span>Analysis progress</span>
        <strong>{progress}%</strong>
      </div>
      <div
        className={styles.progressTrack}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progress}
      >
        <span style={{ width: `${progress}%` }} />
      </div>

      <dl className={styles.details}>
        <div>
          <dt>Request ID</dt>
          <dd>
            <code>{record.id}</code>
            <button
              type="button"
              aria-label="Copy request ID"
              title="Copy request ID"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(record.id);
                  setCopied(true);
                  window.setTimeout(() => setCopied(false), 1600);
                } catch {
                  setCopied(false);
                }
              }}
            >
              {copied ? <Check size={15} /> : <Clipboard size={15} />}
            </button>
          </dd>
        </div>
        <div>
          <dt>Input</dt>
          <dd>{record.type.toLowerCase()}</dd>
        </div>
        <div>
          <dt>Created</dt>
          <dd>{new Date(record.createdAt).toLocaleString()}</dd>
        </div>
      </dl>

      {liveUpdatesPaused && (
        <p className={styles.partial}>
          The request was created, but the latest status could not be fetched. Keep the
          request ID for follow-up.
        </p>
      )}
    </section>
  );
}
