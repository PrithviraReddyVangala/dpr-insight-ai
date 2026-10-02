export function PdfPreview({ fileUrl }: { fileUrl: string }) {
  return (
    <div className="h-full overflow-hidden rounded-card border border-border bg-surface shadow-panel">
      <object data={fileUrl} type="application/pdf" className="h-full w-full">
        <div className="flex h-full items-center justify-center p-6 text-center text-sm text-ink-muted">
          Your browser can't preview PDFs inline.{" "}
          <a href={fileUrl} className="text-accent underline" target="_blank" rel="noreferrer">
            Open the file directly
          </a>
          .
        </div>
      </object>
    </div>
  );
}
