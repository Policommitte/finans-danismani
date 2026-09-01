"use client";

import type { PendingAttachment } from "./AttachmentMenu";

function FileBadgeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

export function AttachmentPreview({
  attachment,
  onRemove,
}: {
  attachment: PendingAttachment;
  onRemove: () => void;
}) {
  return (
    <div className="flex items-center gap-2 border-t app-border px-3 pt-2.5">
      <div className="relative flex items-center gap-2 rounded-md border app-border bg-[var(--color-surface)] px-2 py-1.5">
        {attachment.kind === "image" ? (
          <img src={attachment.dataUrl} alt="" className="h-9 w-9 rounded object-cover" />
        ) : (
          <span className="grid h-9 w-9 place-items-center rounded bg-[var(--color-primary-soft)] text-[var(--color-primary)]">
            <FileBadgeIcon />
          </span>
        )}
        <span className="max-w-[160px] truncate text-xs font-medium text-[var(--color-text)]">
          {attachment.filename}
        </span>
        <button
          type="button"
          aria-label="Eki kaldır"
          onClick={onRemove}
          className="grid h-5 w-5 shrink-0 place-items-center rounded-full text-[var(--color-muted)] transition hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger-text)]"
        >
          <CloseIcon />
        </button>
      </div>
    </div>
  );
}
