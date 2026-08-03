"use client";

import Image from "next/image";
import { FileType2, ImagePlus, Trash2, Video } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import styles from "./media-dropzone.module.css";

type MultimodalComposerProps = {
  value: string;
  onValueChange: (value: string) => void;
  file: File | null;
  onFileChange: (file: File | null) => void;
  maxLength: number;
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

export function MultimodalComposer({
  value,
  onValueChange,
  file,
  onFileChange,
  maxLength,
  disabled = false,
}: MultimodalComposerProps) {
  const promptId = useId();
  const imageInputRef = useRef<HTMLInputElement>(null);
  const videoInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const isImage = file?.type.startsWith("image/") ?? false;
  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function chooseFile(nextFile: File | undefined) {
    if (nextFile) onFileChange(nextFile);
    if (imageInputRef.current) imageInputRef.current.value = "";
    if (videoInputRef.current) videoInputRef.current.value = "";
  }

  return (
    <div
      className={`${styles.composer} ${dragActive ? styles.dragActive : ""}`}
      onDragEnter={(event) => {
        event.preventDefault();
        if (!disabled) setDragActive(true);
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
        if (!disabled) chooseFile(event.dataTransfer.files?.[0]);
      }}
    >
      <div className={styles.promptHeader}>
        <label htmlFor={promptId}>What should we verify?</label>
        <span>{value.length.toLocaleString()} / {maxLength.toLocaleString()}</span>
      </div>

      <textarea
        id={promptId}
        value={value}
        onChange={(event) => onValueChange(event.target.value)}
        maxLength={maxLength + 1}
        placeholder="Paste a claim or public URL, or ask a question about an attached image or video..."
        disabled={disabled}
      />

      {file && previewUrl && (
        <section className={styles.attachment} aria-label="Attached evidence">
          <div className={styles.preview}>
            {isImage ? (
              <Image
                src={previewUrl}
                alt={`Preview of ${file.name}`}
                fill
                sizes="(max-width: 760px) 100vw, 720px"
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
              <FileType2 size={17} />
            </span>
            <span className={styles.fileCopy}>
              <strong>{file.name}</strong>
              <small>{file.type || "Unknown type"} · {formatBytes(file.size)}</small>
            </span>
            <button
              className={styles.removeButton}
              type="button"
              onClick={() => onFileChange(null)}
              aria-label="Remove attachment"
              title="Remove attachment"
              disabled={disabled}
            >
              <Trash2 size={17} />
            </button>
          </div>
        </section>
      )}

      <div className={styles.toolbar}>
        <div className={styles.attachmentActions}>
          <input
            ref={imageInputRef}
            className="visually-hidden"
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            onChange={(event) => chooseFile(event.target.files?.[0])}
            disabled={disabled}
            aria-hidden="true"
            tabIndex={-1}
          />
          <input
            ref={videoInputRef}
            className="visually-hidden"
            type="file"
            accept="video/mp4,video/quicktime,video/webm"
            onChange={(event) => chooseFile(event.target.files?.[0])}
            disabled={disabled}
            aria-hidden="true"
            tabIndex={-1}
          />
          <button
            type="button"
            onClick={() => imageInputRef.current?.click()}
            disabled={disabled}
            title="Attach image"
          >
            <ImagePlus size={17} aria-hidden="true" />
            Image
          </button>
          <button
            type="button"
            onClick={() => videoInputRef.current?.click()}
            disabled={disabled}
            title="Attach video"
          >
            <Video size={17} aria-hidden="true" />
            Video
          </button>
        </div>
        <span className={styles.inputSignal}>
          {file ? `${isImage ? "Image" : "Video"} attached` : "Text, URL, image or video"}
        </span>
      </div>

      {dragActive && <div className={styles.dropOverlay}>Drop attachment</div>}
    </div>
  );
}
