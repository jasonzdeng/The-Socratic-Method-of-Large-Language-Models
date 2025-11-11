"use client";

import React, { useMemo, useState } from "react";
import ArtifactEditor from "../../../components/ArtifactEditor";
import FinancialChart from "../../../components/FinancialChart";

type TimelineEventType = "round" | "tool" | "verdict";

type TimelineEvent = {
  id: string;
  type: TimelineEventType;
  agent: string;
  claimTags: string[];
  timestamp: string;
  title: string;
  description: string;
  payload?: Record<string, unknown>;
};

const mockEvents: TimelineEvent[] = [
  {
    id: "round-1",
    type: "round",
    agent: "debater-1",
    claimTags: ["macroeconomics"],
    timestamp: "2024-04-12T09:30:00Z",
    title: "Opening Argument",
    description:
      "Debater 1 provides the initial overview focusing on inflation expectations.",
  },
  {
    id: "tool-1",
    type: "tool",
    agent: "quant-tool",
    claimTags: ["financials", "equities"],
    timestamp: "2024-04-12T09:45:00Z",
    title: "Discounted Cash Flow Analysis",
    description:
      "Quant tool generated a DCF valuation using the latest quarterly filings.",
    payload: {
      dataSource: "s3://research-data/valuations/q1-2024.json",
      chartData: [
        { label: "Base", value: 120 },
        { label: "Bull", value: 160 },
        { label: "Bear", value: 90 },
      ],
    },
  },
  {
    id: "verdict-1",
    type: "verdict",
    agent: "judge",
    claimTags: ["consensus"],
    timestamp: "2024-04-12T10:30:00Z",
    title: "Interim Verdict",
    description:
      "Judge finds that the bear case lacks sufficient evidence and requests further clarification.",
  },
];

type TimelineFilters = {
  agent: string;
  claimTag: string;
  eventTypes: Record<TimelineEventType, boolean>;
};

const defaultFilters: TimelineFilters = {
  agent: "",
  claimTag: "",
  eventTypes: {
    round: true,
    tool: true,
    verdict: true,
  },
};

function TimelineFiltersPanel({
  filters,
  onChange,
  agents,
  claimTags,
}: {
  filters: TimelineFilters;
  onChange: (filters: TimelineFilters) => void;
  agents: string[];
  claimTags: string[];
}) {
  const toggleType = (type: TimelineEventType) => {
    onChange({
      ...filters,
      eventTypes: {
        ...filters.eventTypes,
        [type]: !filters.eventTypes[type],
      },
    });
  };

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-lg font-semibold text-slate-800">Timeline filters</h2>
      <div className="mb-4 grid gap-4 md:grid-cols-2">
        <label className="flex flex-col text-sm text-slate-600">
          Agent
          <select
            value={filters.agent}
            onChange={(event) =>
              onChange({ ...filters, agent: event.target.value })
            }
            className="mt-1 rounded border border-slate-300 p-2"
          >
            <option value="">All agents</option>
            {agents.map((agent) => (
              <option key={agent} value={agent}>
                {agent}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-sm text-slate-600">
          Claim tag
          <select
            value={filters.claimTag}
            onChange={(event) =>
              onChange({ ...filters, claimTag: event.target.value })
            }
            className="mt-1 rounded border border-slate-300 p-2"
          >
            <option value="">All claim tags</option>
            {claimTags.map((tag) => (
              <option key={tag} value={tag}>
                {tag}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="flex flex-wrap gap-3">
        {(
          ["round", "tool", "verdict"] as TimelineEventType[]
        ).map((eventType) => (
          <button
            key={eventType}
            onClick={() => toggleType(eventType)}
            className={`rounded px-3 py-1 text-sm font-medium transition-colors ${
              filters.eventTypes[eventType]
                ? "bg-slate-900 text-white"
                : "bg-slate-200 text-slate-600"
            }`}
            type="button"
          >
            {eventType.charAt(0).toUpperCase() + eventType.slice(1)} events
          </button>
        ))}
      </div>
    </section>
  );
}

function TimelineEventCard({ event }: { event: TimelineEvent }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between text-sm text-slate-500">
        <span className="font-semibold text-slate-700">{event.agent}</span>
        <time dateTime={event.timestamp}>
          {new Date(event.timestamp).toLocaleString()}
        </time>
      </div>
      <h3 className="mt-2 text-lg font-semibold text-slate-900">{event.title}</h3>
      <p className="mt-2 text-slate-600">{event.description}</p>
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        {event.claimTags.map((tag) => (
          <span
            key={tag}
            className="rounded bg-slate-100 px-2 py-1 text-slate-600"
          >
            #{tag}
          </span>
        ))}
      </div>
      {event.type === "tool" && event.payload?.chartData && (
        <div className="mt-4">
          <FinancialChart
            title="Scenario valuation"
            data={(event.payload.chartData as { label: string; value: number }[]).map(
              (row) => ({
                name: row.label,
                value: row.value,
                drilldown: {
                  dataSource: (event.payload?.dataSource as string) ?? "",
                  context: event.title,
                },
              })
            )}
            onSelectDataPoint={(point) => {
              console.info("Drill-down requested", point);
            }}
          />
        </div>
      )}
    </article>
  );
}

export default function TopicTimelinePage() {
  const [filters, setFilters] = useState<TimelineFilters>(defaultFilters);

  const allAgents = useMemo(
    () => Array.from(new Set(mockEvents.map((event) => event.agent))),
    []
  );
  const allClaimTags = useMemo(
    () =>
      Array.from(
        new Set(
          mockEvents.flatMap((event) => event.claimTags).sort((a, b) => a.localeCompare(b))
        )
      ),
    []
  );

  const filteredEvents = useMemo(() => {
    return mockEvents.filter((event) => {
      if (!filters.eventTypes[event.type]) {
        return false;
      }

      if (filters.agent && event.agent !== filters.agent) {
        return false;
      }

      if (filters.claimTag && !event.claimTags.includes(filters.claimTag)) {
        return false;
      }

      return true;
    });
  }, [filters]);

  return (
    <div className="flex flex-col gap-8 bg-slate-50 p-8">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">
          Timeline overview for topic #{"{"}params.id{"}"}
        </h1>
        <p className="mt-2 text-slate-600">
          Review the debate rounds, tool outputs, and judge verdicts. Use filters to
          focus on specific agents or claim tags.
        </p>
      </header>

      <TimelineFiltersPanel
        filters={filters}
        onChange={setFilters}
        agents={allAgents}
        claimTags={allClaimTags}
      />

      <section className="grid gap-4">
        {filteredEvents.map((event) => (
          <TimelineEventCard key={event.id} event={event} />
        ))}
        {filteredEvents.length === 0 && (
          <p className="text-sm text-slate-600">
            No events match the selected filters.
          </p>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-slate-900">Compose artifact</h2>
        <p className="mt-2 text-sm text-slate-600">
          Summarize the consensus or request manual intervention by publishing a
          markdown artifact. Agent outputs can be inserted as citations, and
          published artifacts are stored in the shared `artifacts/` bucket.
        </p>
        <div className="mt-6">
          <ArtifactEditor
            topicId="sample-topic"
            availableOutputs={mockEvents.map((event) => ({
              id: event.id,
              title: event.title,
              content: event.description,
              metadata: {
                agent: event.agent,
                timestamp: event.timestamp,
                claimTags: event.claimTags,
              },
            }))}
          />
        </div>
      </section>
    </div>
  );
}
