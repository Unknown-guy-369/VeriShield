"use client";

import { ArrowRight, RotateCcw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { AnalysisRecord } from "@/lib/analysis";
import { createAnalysis, getAnalysis } from "@/lib/api";
import { MAX_TEXT_LENGTH, validateIntake } from "@/lib/validation";
import { EvidenceTrace } from "./evidence-trace";
import { MultimodalComposer } from "./media-dropzone";
import { RequestReceipt } from "./request-receipt";
import styles from "./analyzer-workspace.module.css";

type Phase = "idle" | "submitting" | "success" | "error";

const languages = [
  ["en", "English"],
  ["hi", "Hindi"],
  ["ta", "Tamil"],
  ["te", "Telugu"],
  ["ml", "Malayalam"],
  ["bn", "Bengali"],
];

const terminalStatuses = new Set(["COMPLETED", "FAILED"]);

export function AnalyzerWorkspace() {
  const [input, setInput] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preferredLanguage, setPreferredLanguage] = useState("en");
  const [phase, setPhase] = useState<Phase>("idle");
  const [record, setRecord] = useState<AnalysisRecord | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [liveUpdatesPaused, setLiveUpdatesPaused] = useState(false);

  const draft = useMemo(() => ({ input, file }), [file, input]);

  useEffect(() => {
    if (!record || phase !== "success" || terminalStatuses.has(record.status)) return;

    let active = true;
    const timer = window.setInterval(async () => {
      try {
        const next = await getAnalysis(record.id);
        if (active) {
          setRecord(next);
          setLiveUpdatesPaused(false);
        }
      } catch {
        if (active) setLiveUpdatesPaused(true);
      }
    }, 5000);

    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [phase, record]);

  function resetWorkspace() {
    setInput("");
    setFile(null);
    setPhase("idle");
    setRecord(null);
    setError(null);
    setValidationMessage(null);
    setLiveUpdatesPaused(false);
  }

  async function submit() {
    const validationError = validateIntake(draft);
    if (validationError) {
      setValidationMessage(validationError);
      return;
    }

    setValidationMessage(null);
    setError(null);
    setRecord(null);
    setLiveUpdatesPaused(false);
    setPhase("submitting");

    try {
      const result = await createAnalysis({
        input: input.trim(),
        file,
        preferredLanguage,
      });
      setRecord(result);
      setPhase("success");
    } catch (caught) {
      setError(caught instanceof Error ? caught : new Error("Request failed."));
      setPhase("error");
    }
  }

  const busy = phase === "submitting";

  return (
    <div className={styles.page}>
      <section className={styles.intro} aria-labelledby="workspace-title">
        <p className={styles.eyebrow}>Multimodal verification intake</p>
        <h1 id="workspace-title">Bring the evidence. Ask the real question.</h1>
        <p className={styles.lede}>
          Add a claim, link, image, or video in one place. VeriShield identifies the
          content type and routes the right verification checks automatically.
        </p>
      </section>

      <div className={styles.workspace}>
        <section className={styles.analyzer} aria-labelledby="analyzer-heading">
          <div className={styles.sectionHeading}>
            <div>
              <p>New verification</p>
              <h2 id="analyzer-heading">What needs checking?</h2>
            </div>
            {phase !== "idle" && (
              <button className={styles.resetButton} type="button" onClick={resetWorkspace}>
                <RotateCcw size={15} aria-hidden="true" />
                Start over
              </button>
            )}
          </div>

          <MultimodalComposer
            value={input}
            onValueChange={setInput}
            file={file}
            onFileChange={setFile}
            maxLength={MAX_TEXT_LENGTH}
            disabled={busy}
          />

          <div className={styles.controls}>
            <label className={styles.languageField}>
              <span>Report language</span>
              <select
                value={preferredLanguage}
                onChange={(event) => setPreferredLanguage(event.target.value)}
                disabled={busy}
              >
                {languages.map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
            <button className={styles.submitButton} type="button" onClick={submit} disabled={busy}>
              {busy ? "Submitting evidence" : "Analyze evidence"}
              <ArrowRight size={17} aria-hidden="true" />
            </button>
          </div>

          {validationMessage && (
            <p className={styles.validation} role="alert">{validationMessage}</p>
          )}

          <RequestReceipt
            phase={phase}
            record={record}
            error={error}
            liveUpdatesPaused={liveUpdatesPaused}
          />
        </section>

        <EvidenceTrace
          phase={phase}
          record={record}
          liveUpdatesPaused={liveUpdatesPaused}
        />
      </div>

      <footer className={styles.footerNote}>
        <span>Current stage</span>
        <p>
          Intake, text evidence retrieval, stance analysis, and deterministic scoring
          run through the same traceable analysis lifecycle.
        </p>
      </footer>
    </div>
  );
}
