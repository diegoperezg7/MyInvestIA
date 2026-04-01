"use client";

import { useRef, useState } from "react";

export default function ImportExport() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleExport = () => {
    window.open("/api/v1/portfolio/export", "_blank");
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const resp = await fetch("/api/v1/portfolio/import", {
        method: "POST",
        body: formData,
      });
      const data = await resp.json();
      setResult(`Imported ${data.imported} holdings: ${data.symbols.join(", ")}`);
    } catch {
      setResult("Import failed");
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handleExport}
        className="text-xs text-oracle-accent hover:text-oracle-accent/80 px-2 py-1 border border-oracle-border rounded"
      >
        Export CSV
      </button>
      <label className="text-xs text-oracle-accent hover:text-oracle-accent/80 px-2 py-1 border border-oracle-border rounded cursor-pointer">
        {importing ? "Importing..." : "Import CSV"}
        <input
          ref={fileRef}
          type="file"
          accept=".csv"
          onChange={handleImport}
          className="hidden"
        />
      </label>
      {result && <span className="text-xs text-oracle-muted">{result}</span>}
    </div>
  );
}
