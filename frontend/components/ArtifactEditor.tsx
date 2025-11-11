"use client";

import React, { useMemo, useState } from "react";

export type AgentOutput = {
  id: string;
  title: string;
  content: string;
  metadata?: Record<string, unknown>;
};

type PublishStatus = "idle" | "publishing" | "success" | "error";

type ArtifactEditorProps = {
  topicId: string;
  availableOutputs: AgentOutput[];
};

function formatOutputMetadata(metadata?: Record<string, unknown>) {
  if (!metadata) {
    return "";
  }

  return Object.entries(metadata)
    .map(([key, value]) => `- **${key}**: ${value}`)
    .join("\n");
}

export default function ArtifactEditor({
  topicId,
  availableOutputs,
}: ArtifactEditorProps) {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [status, setStatus] = useState<PublishStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const suggestedCitations = useMemo(() => {
    return availableOutputs.map((output) => {
      const metadataSection = formatOutputMetadata(output.metadata);
      return `> ${output.title}\n\n${output.content}\n\n${metadataSection}`.trim();
    });
  }, [availableOutputs]);

  const handleInsertOutput = (output: AgentOutput) => {
    const metadata = formatOutputMetadata(output.metadata);
    const snippet =
      `### ${output.title}\n\n${output.content}` +
      (metadata ? `\n\n${metadata}` : "");
    setBody((previous) =>
      previous ? `${previous}\n\n${snippet}` : snippet
    );
  };

  const handlePublish = async () => {
    if (!title.trim() || !body.trim()) {
      setErrorMessage("Title and body are required before publishing.");
      return;
    }

    setStatus("publishing");
    setErrorMessage(null);

    try {
      const payload = {
        topic_id: topicId,
        title,
        body_markdown: body,
        storage_prefix: "artifacts/",
      };

      const response = await fetch("/api/artifacts/export", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Failed to publish artifact: ${response.statusText}`);
      }

      setStatus("success");
    } catch (error) {
      console.error("Artifact publication failed", error);
      setStatus("error");
      setErrorMessage(
        error instanceof Error ? error.message : "Unknown error while publishing"
      );
    }
  };

  const statusMessage = useMemo(() => {
    switch (status) {
      case "publishing":
        return "Publishing artifact to object storage...";
      case "success":
        return "Artifact successfully published.";
      case "error":
        return errorMessage ?? "Artifact publication failed.";
      default:
        return "";
    }
  }, [status, errorMessage]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-slate-700" htmlFor="artifact-title">
          Artifact title
        </label>
        <input
          id="artifact-title"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          className="rounded border border-slate-300 p-2"
          placeholder="Consensus summary"
        />
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-slate-700" htmlFor="artifact-body">
          Markdown body
        </label>
        <textarea
          id="artifact-body"
          value={body}
          onChange={(event) => setBody(event.target.value)}
          className="h-48 rounded border border-slate-300 p-3 font-mono"
          placeholder="Summaries, citations, and action items..."
        />
        <p className="text-xs text-slate-500">
          Agent outputs can be inserted below. Artifacts are stored under the
          <code className="mx-1 rounded bg-slate-100 px-1">artifacts/</code> prefix
          in S3 or GCS for later retrieval.
        </p>
      </div>

      <div className="space-y-3 rounded border border-slate-200 bg-slate-50 p-4">
        <h3 className="text-sm font-semibold text-slate-700">Available agent outputs</h3>
        <ul className="space-y-2">
          {availableOutputs.map((output) => (
            <li key={output.id} className="rounded border border-slate-200 bg-white p-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-slate-800">{output.title}</p>
                  <p className="text-xs text-slate-500">{output.metadata?.agent as string}</p>
                </div>
                <button
                  type="button"
                  className="rounded bg-slate-900 px-3 py-1 text-xs font-semibold text-white hover:bg-slate-700"
                  onClick={() => handleInsertOutput(output)}
                >
                  Insert
                </button>
              </div>
              <p className="mt-2 text-sm text-slate-600">{output.content}</p>
            </li>
          ))}
        </ul>
        {suggestedCitations.length > 0 && (
          <details className="rounded border border-dashed border-slate-300 bg-white p-3 text-sm text-slate-600">
            <summary className="cursor-pointer text-slate-700">
              Suggested citation snippets
            </summary>
            <ul className="mt-2 list-disc space-y-2 pl-5">
              {suggestedCitations.map((snippet, index) => (
                <li key={index}>
                  <pre className="whitespace-pre-wrap rounded bg-slate-100 p-2 text-xs">
                    {snippet}
                  </pre>
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={handlePublish}
          disabled={status === "publishing"}
          className="rounded bg-emerald-600 px-4 py-2 font-semibold text-white transition-colors hover:bg-emerald-500 disabled:opacity-50"
        >
          {status === "publishing" ? "Publishing..." : "Publish artifact"}
        </button>
        {statusMessage && (
          <span
            className={`text-sm ${
              status === "error" ? "text-red-600" : "text-slate-600"
            }`}
          >
            {statusMessage}
          </span>
        )}
      </div>
    </div>
  );
}
