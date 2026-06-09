"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL, ApiError, apiPost } from "@/lib/api/client";
import type { SessionState } from "@/lib/api/types";
import { Button } from "@/components/ui/Button";

/*
 * Export / import controls.
 * - Export downloads GET /sessions/{id}/export as a JSON file.
 * - Import POSTs a chosen record to /sessions/import and routes to the new id.
 */
export function SessionActions({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<"export" | "import" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleExport() {
    setBusy("export");
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE_URL}/sessions/${sessionId}/export`,
      );
      if (!res.ok) throw new Error(`Export failed (${res.status})`);
      const record = await res.json();
      const blob = new Blob([JSON.stringify(record, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `session-${sessionId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setBusy(null);
    }
  }

  async function handleImportFile(file: File) {
    setBusy("import");
    setError(null);
    try {
      const record = JSON.parse(await file.text());
      const state = await apiPost<SessionState>("/sessions/import", record);
      router.push(`/session/${state.session_id}`);
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? e.displayMessage
          : e instanceof Error
            ? e.message
            : "Import failed";
      setError(msg);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2">
        <Button
          variant="secondary"
          onClick={handleExport}
          disabled={busy !== null}
        >
          {busy === "export" ? "Exporting…" : "Export"}
        </Button>
        <Button
          variant="secondary"
          onClick={() => fileInput.current?.click()}
          disabled={busy !== null}
        >
          {busy === "import" ? "Importing…" : "Import"}
        </Button>
        <input
          ref={fileInput}
          type="file"
          accept="application/json"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleImportFile(file);
            e.target.value = "";
          }}
        />
      </div>
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
}
