"use client";

import Image from "next/image";
import {
  FileType2,
  Image as ImageIcon,
  RefreshCw,
  Trash2,
  UploadCloud,
  Video,
} from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { AnalysisType } from "@/lib/analysis";
import styles from "./media-dropzone.module.css";

type MediaDropzoneProps = {
  type: Extract<AnalysisType, "IMAGE" | "VIDEO">;
  file: File | null;
  onFileChange: (file: File | null) => void;
  disabled?: boolean;
};

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = units[0];
  for (let index = 1; value >= 1024 && index < units.length; index += 1) {
    value /= 1024;
    unit = units[index];
  }
  return `${value.toFixed(value >= 10 ? 1 : 2)} ${unit}`;
}

export function MediaDropzone({
  type,
  file,
  onFileChange,
  disabled = false,
}: MediaDropzoneProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const isImage = type === "IMAGE";
  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function chooseFile(nextFile: File | undefined) {
    if (nextFile) onFileChange(nextFile);
    if (inputRef.current) inputRef.current.value = "";
  }

  const input = (
    <input
      ref={inputRef}
      id={inputId}
      className="visually-hidden"
      type="file"
      accept={isImage ? "image/*" : "video/*"}
      onChange={(event) => chooseFile(event.target.files?.[0])}
      disabled={disabled}
    />
  );

  if (file && previewUrl) {
    return (
      <section className={styles.selected} aria-label="Selected file">
        <div className={styles.preview}>
          {isImage ? (
            <Image
              src={previewUrl}
              alt={`Preview of ${file.name}`}
              fill
              sizes="(max-width: 760px) 100vw, 620px"
              unoptimized
            />
          ) : (
            <video src={previewUrl} controls preload="metadata">
              Your browser cannot preview this video.
            </video>
          )}
        </div>
        <div className={styles.fileRow}>
          <span className={styles.fileIcon} aria-hidden="true">
            <FileType2 size={18} />
          </span>
          <span className={styles.fileCopy}>
            <strong>{file.name}</strong>
            <small>
              {file.type || "Unknown type"} · {formatBytes(file.size)}
            </small>
          </span>
          <span className={styles.actions}>
            {input}
            <button
              className={styles.iconButton}
              type="button"
              onClick={() => inputRef.current?.click()}
              aria-label="Replace file"
              title="Replace file"
              disabled={disabled}
            >
              <RefreshCw size={17} />
            </button>
            <button
              className={styles.iconButton}
              type="button"
              onClick={() => onFileChange(null)}
              aria-label="Remove file"
              title="Remove file"
              disabled={disabled}
            >
              <Trash2 size={17} />
            </button>
          </span>
        </div>
      </section>
    );
  }

  return (
    <div
      className={`${styles.dropzone} ${dragActive ? styles.dragActive : ""}`}
      onDragEnter={(event) => {
        event.preventDefault();
        setDragActive(true);
      }}
      onDragOver={(event) => event.preventDefault()}
      onDragLeave={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node)) {
          setDragActive(false);
        }
      }}
      onDrop={(event) => {
        event.preventDefault();
        setDragActive(false);
        chooseFile(event.dataTransfer.files?.[0]);
      }}
    >
      {input}
      <label className={styles.dropLabel} htmlFor={inputId}>
        <span className={styles.uploadIcon} aria-hidden="true">
          {isImage ? <ImageIcon size={26} /> : <Video size={26} />}
        </span>
        <span>
          <strong>Drop {isImage ? "an image" : "a video"} here</strong>
          <small>or browse from this device</small>
        </span>
        <span className={styles.browse}>
          <UploadCloud size={16} aria-hidden="true" />
          Browse file
        </span>
      </label>
      <p>
        {isImage
          ? "JPEG, PNG, WebP or GIF · up to 15 MB"
          : "Common browser video formats · up to 150 MB"}
      </p>
    </div>
  );
}
