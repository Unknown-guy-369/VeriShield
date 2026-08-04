"use client";

import {
  Check,
  CheckCircle2,
  Clipboard,
  ExternalLink,
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
  const result = record.result;
  const scoreForClaim = (claimId: string) =>
    result?.scores.find((score) => score.claim_id === claimId);
  const stanceForClaim = (claimId: string) =>
    result?.stances.find((stance) => stance.claim_id === claimId);
  const evidenceForClaim = (claimId: string) =>
    result?.evidence.filter((item) => item.claim_id === claimId) ?? [];

  const overallStance = result?.stances.some((stance) => stance.stance === "contradicted")
    ? "Contradicted"
    : result?.stances.some((stance) => stance.stance === "supported")
      ? "Supported"
      : "Insufficient evidence";
  const overallScore = result && result.scores.length > 0
    ? Math.round(result.scores.reduce((total, item) => total + item.score, 0) / result.scores.length)
    : null;

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

      {result && result.claims.length > 0 && (
        <section className={styles.report} aria-labelledby="analysis-result-title">
          <div className={styles.reportHeader}>
            <div>
              <p className={styles.reportEyebrow}>Verification result</p>
              <h3 id="analysis-result-title">{overallStance}</h3>
            </div>
            {overallScore !== null && (
              <div className={styles.scoreBadge}>
                <strong>{overallScore}</strong>
                <span>/ 100 credibility</span>
              </div>
            )}
          </div>

          <div className={styles.claimList}>
            {result.claims.map((claim) => {
              const stance = stanceForClaim(claim.id);
              const score = scoreForClaim(claim.id);
              const evidence = evidenceForClaim(claim.id);
              return (
                <article className={styles.claim} key={claim.id}>
                  <div className={styles.claimHeader}>
                    <p>{claim.text}</p>
                    <span data-stance={stance?.stance ?? "insufficient"}>
                      {stance?.stance ?? "insufficient"}
                    </span>
                  </div>
                  <div className={styles.claimMeta}>
                    <span>{score?.score ?? 0}/100 score</span>
                    <span>{evidence.length} source{evidence.length === 1 ? "" : "s"}</span>
                  </div>
                  {stance?.reasoning && <p className={styles.reasoning}>{stance.reasoning}</p>}
                  {evidence.length > 0 && (
                    <ul className={styles.sourceList}>
                      {evidence.map((item) => (
                        <li key={item.id}>
                          <a href={item.url} target="_blank" rel="noreferrer">
                            <span>{item.title}</span>
                            <ExternalLink size={13} aria-hidden="true" />
                          </a>
                          <small>{item.publisher ?? item.provider_name ?? "Evidence provider"}</small>
                          {item.passage && <p>{item.passage}</p>}
                        </li>
                      ))}
                    </ul>
                  )}
                </article>
              );
            })}
          </div>
        </section>
      )}

      {record.type === "TEXT" && record.status === "COMPLETED" && !result && (
        <p className={styles.partial}>
          Processing completed, but the API returned no structured verification result.
          Check the backend logs for this request ID.
        </p>
      )}

      {liveUpdatesPaused && (
        <p className={styles.partial}>
          The request was created, but the latest status could not be fetched. Keep the
          request ID for follow-up.
        </p>
      )}
    </section>
  );
}
