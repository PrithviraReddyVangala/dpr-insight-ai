import { UploadCloud } from "lucide-react";
import { useCallback, useRef, useState } from "react";

export function UploadZone({ onUpload }: { onUpload: (file: File) => void }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      const file = files?.[0];
      if (file && file.type === "application/pdf") {
        onUpload(file);
      }
    },
    [onUpload]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      className={`group flex cursor-pointer flex-col items-center justify-center gap-2.5 rounded-card border border-dashed px-6 py-10 text-center transition-colors ${
        dragging
          ? "border-accent bg-accent-soft"
          : "border-border-strong hover:border-accent/50 hover:bg-accent-soft/40"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <div className={`flex h-9 w-9 items-center justify-center rounded-full ${dragging ? "bg-accent text-white" : "bg-accent-soft text-accent"}`}>
        <UploadCloud size={18} strokeWidth={2} />
      </div>
      <div>
        <p className="text-sm font-medium text-ink">Drop a DPR here, or click to upload</p>
        <p className="mt-0.5 text-xs text-ink-faint">PDF, up to 200MB</p>
      </div>
    </div>
  );
}
