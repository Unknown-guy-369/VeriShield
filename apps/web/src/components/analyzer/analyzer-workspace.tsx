"use client";

import {
  ArrowRight,
  FileText,
  Image as ImageIcon,
  Link2,
  RotateCcw,
  Video,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { AnalysisRecord, AnalysisType } from "@/lib/analysis";
import { createAnalysis, getAnalysis } from "@/lib/api";
import { MAX_TEXT_LENGTH, validateIntake } from "@/lib/validation";
import { EvidenceTrace } from "./evidence-trace";
import { MediaDropzone } from "./media-dropzone";
import { RequestReceipt } from "./request-receipt";
import styles from "./analyzer-workspace.module.css";

type Phase = "idle" | "submitting" | "success" | "error";

const inputModes: Array<{
  type: AnalysisType;
  label: string;
  icon: typeof FileText;
}> = [
  { type: "TEXT", label: "Text", icon: FileText },
  { type: "URL", label: "URL", icon: Link2 },
  { type: "IMAGE", label: "Image", icon: ImageIcon },
  { type: "VIDEO", label: "Video", icon: Video },
];

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
  const [type, setType] = useState<AnalysisType>("TEXT");
  const [text, setText] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preferredLanguage, setPreferredLanguage] = useState("en");
  const [phase, setPhase] = useState<Phase>("idle");
  const [record, setRecord] = useState<AnalysisRecord | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [liveUpdatesPaused, setLiveUpdatesPaused] = useState(false);

  const draft = useMemo(
    () => ({ type, text, sourceUrl, file }),
    [file, sourceUrl, text, type],
  );

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

  function selectType(nextType: AnalysisType) {
    setType(nextType);
    setFile(null);
    setValidationMessage(null);
    setError(null);
  }

  function resetWorkspace() {
    setText("");
    setSourceUrl("");
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
      const result =
        type === "TEXT"
          ? await createAnalysis({ type, text: text.trim(), preferredLanguage })
          : type === "URL"
            ? await createAnalysis({
                type,
                sourceUrl: sourceUrl.trim(),
                preferredLanguage,
              })
            : await createAnalysis({
                type,
                file: file as File,
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
        <h1 id="workspace-title">Start with the content in question.</h1>
        <p className={styles.lede}>
          Submit a claim, public link, image, or video. VeriShield records the input
          first, then routes it toward independent signal and evidence checks.
        </p>
      </section>

      <div className={styles.workspace}>
        <section className={styles.analyzer} aria-labelledby="analyzer-heading">
          <div className={styles.sectionHeading}>
            <div>
              <p>New verification</p>
              <h2 id="analyzer-heading">Choose an input</h2>
            </div>
            {phase !== "idle" && (
              <button className={styles.resetButton} type="button" onClick={resetWorkspace}>
                <RotateCcw size={15} aria-hidden="true" />
                Start over
              </button>
            )}
          </div>

          <div className={styles.segmented} role="tablist" aria-label="Input type">
            {inputModes.map((mode) => {
              const Icon = mode.icon;
              return (
                <button
                  key={mode.type}
                  type="button"
                  role="tab"
                  aria-selected={type === mode.type}
                  className={type === mode.type ? styles.activeMode : undefined}
                  onClick={() => selectType(mode.type)}
                  disabled={busy}
                >
                  <Icon size={17} aria-hidden="true" />
                  {mode.label}
                </button>
              );
            })}
          </div>

          <div className={styles.inputArea} role="tabpanel">
            {type === "TEXT" && (
              <label className={styles.field}>
                <span>
                  Claim, caption, or message
                  <small>{text.length.toLocaleString()} / {MAX_TEXT_LENGTH.toLocaleString()}</small>
                </span>
                <textarea
                  value={text}
                  onChange={(event) => setText(event.target.value)}
                  maxLength={MAX_TEXT_LENGTH + 1}
                  placeholder="Paste the message or claim exactly as it appeared..."
                  disabled={busy}
                  aria-describedby="text-help"
                />
                <small id="text-help">
                  Preserve dates, names, locations, and the original wording when possible.
                </small>
              </label>
            )}

            {type === "URL" && (
              <label className={styles.field}>
                <span>Public content URL</span>
                <div className={styles.urlInput}>
                  <Link2 size={18} aria-hidden="true" />
                  <input
                    type="url"
                    value={sourceUrl}
                    onChange={(event) => setSourceUrl(event.target.value)}
                    placeholder="https://example.com/public-post"
                    disabled={busy}
                    autoCapitalize="none"
                    autoCorrect="off"
                  />
                </div>
                <small>Use a public HTTP or HTTPS page that the evidence service can access.</small>
              </label>
            )}

            {(type === "IMAGE" || type === "VIDEO") && (
              <MediaDropzone
                type={type}
                file={file}
                onFileChange={setFile}
                disabled={busy}
              />
            )}
          </div>

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
              {busy ? "Submitting content" : "Analyze content"}
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
          Intake and persistence are active. Forensic models, evidence retrieval, and final
          credibility scoring connect to this request lifecycle next.
        </p>
      </footer>
    </div>
  );
}
