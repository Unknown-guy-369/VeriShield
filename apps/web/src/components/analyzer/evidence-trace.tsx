import {
  BookOpenCheck,
  Check,
  CircleAlert,
  Clock3,
  ScanLine,
  Scale,
  UploadCloud,
} from "lucide-react";
import type { AnalysisRecord } from "@/lib/analysis";
import styles from "./evidence-trace.module.css";

type IntakePhase = "idle" | "submitting" | "success" | "error";
type StageState = "ready" | "active" | "complete" | "pending" | "issue";

type EvidenceTraceProps = {
  phase: IntakePhase;
  record: AnalysisRecord | null;
  liveUpdatesPaused: boolean;
};

const terminalStatuses = new Set(["COMPLETED", "FAILED", "CANCELLED"]);

function getStageStates(
  phase: IntakePhase,
  record: AnalysisRecord | null,
  liveUpdatesPaused: boolean,
) {
  const normalizedStatus = record?.status.toUpperCase() ?? "";
  const terminal = terminalStatuses.has(normalizedStatus);

  return {
    input:
      phase === "error"
        ? ("issue" as const)
        : record
          ? ("complete" as const)
          : phase === "submitting"
            ? ("active" as const)
            : ("ready" as const),
    signals:
      normalizedStatus === "FAILED"
        ? ("issue" as const)
        : liveUpdatesPaused
          ? ("issue" as const)
          : record && terminal
            ? ("complete" as const)
            : record
              ? ("active" as const)
              : ("pending" as const),
    sources: "pending" as const,
    verdict: "pending" as const,
  };
}

function StateMark({ state }: { state: StageState }) {
  if (state === "complete") return <Check size={15} aria-hidden="true" />;
  if (state === "issue") return <CircleAlert size={15} aria-hidden="true" />;
  if (state === "active") return <span className={styles.pulse} aria-hidden="true" />;
  return <Clock3 size={14} aria-hidden="true" />;
}

export function EvidenceTrace({
  phase,
  record,
  liveUpdatesPaused,
}: EvidenceTraceProps) {
  const states = getStageStates(phase, record, liveUpdatesPaused);
  const statusLabel = record?.status.toLowerCase().replaceAll("_", " ");
  const stages: Array<{
    key: keyof typeof states;
    label: string;
    description: string;
    icon: typeof UploadCloud;
  }> = [
    {
      key: "input",
      label: "Input",
      description: record
        ? `${record.type.toLowerCase()} received and stored as a traceable request.`
        : phase === "submitting"
          ? "Transferring content to the secure intake API."
          : "Select a format and provide the content to verify.",
      icon: UploadCloud,
    },
    {
      key: "signals",
      label: "Signals",
      description: liveUpdatesPaused
        ? "The request exists, but live processing updates are paused."
        : record
          ? `Analysis service reports ${statusLabel} at ${Math.round(record.progress)}%.`
          : "Claim and media signals begin after intake.",
      icon: ScanLine,
    },
    {
      key: "sources",
      label: "Sources",
      description: "Pending evidence retrieval. No sources are claimed at intake.",
      icon: BookOpenCheck,
    },
    {
      key: "verdict",
      label: "Verdict",
      description: "Pending structured findings, evidence, and confidence checks.",
      icon: Scale,
    },
  ];

  return (
    <aside className={styles.trace} aria-labelledby="evidence-trace-heading">
      <div className={styles.traceHeader}>
        <p>Evidence trace</p>
        <h2 id="evidence-trace-heading">Follow what the system knows</h2>
        <span>
          Each stage stays pending until the platform has produced inspectable output.
        </span>
      </div>

      <ol className={styles.stageList}>
        {stages.map((stage, index) => {
          const Icon = stage.icon;
          const state = states[stage.key];
          return (
            <li
              className={styles.stage}
              data-state={state}
              key={stage.key}
              aria-current={state === "active" || state === "ready" ? "step" : undefined}
            >
              <div className={styles.rail} aria-hidden="true">
                <span className={styles.stageNumber}>{index + 1}</span>
              </div>
              <div className={styles.stageBody}>
                <div className={styles.stageTitle}>
                  <span className={styles.stageIcon} aria-hidden="true">
                    <Icon size={17} />
                  </span>
                  <strong>{stage.label}</strong>
                  <span className={styles.stateMark} title={state}>
                    <StateMark state={state} />
                    <span className="visually-hidden">{state}</span>
                  </span>
                </div>
                <p>{stage.description}</p>
              </div>
            </li>
          );
        })}
      </ol>

      <div className={styles.traceNote}>
        <CircleAlert size={16} aria-hidden="true" />
        <p>
          VeriShield reports evidence and uncertainty. A genuine file does not make its
          caption true.
        </p>
      </div>
    </aside>
  );
}
