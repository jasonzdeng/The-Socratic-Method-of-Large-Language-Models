"use client";

import React from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type FinancialChartPoint = {
  name: string;
  value: number;
  drilldown?: Record<string, unknown>;
};

type FinancialChartProps = {
  title: string;
  data: FinancialChartPoint[];
  onSelectDataPoint?: (point: FinancialChartPoint) => void;
};

export default function FinancialChart({
  title,
  data,
  onSelectDataPoint,
}: FinancialChartProps) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-800">{title}</h3>
        <span className="text-xs text-slate-500">
          Click a point to drill into the linked data source.
        </span>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="name" tick={{ fill: "#475569" }} />
          <YAxis tick={{ fill: "#475569" }} />
          <Tooltip
            formatter={(value: number) => [`$${value.toFixed(2)}`, "Value"]}
            labelStyle={{ color: "#0f172a" }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#2563eb"
            strokeWidth={2}
            activeDot={{ r: 6 }}
            onClick={({ activePayload }) => {
              if (!onSelectDataPoint || !activePayload?.length) {
                return;
              }

              const payload = activePayload[0].payload as FinancialChartPoint;
              onSelectDataPoint(payload);
            }}
          />
        </LineChart>
      </ResponsiveContainer>
      {onSelectDataPoint && (
        <p className="mt-3 text-xs text-slate-500">
          Data sources are supplied by quant research pipelines. The drill-down handler
          can open the referenced dataset or fetch a detailed report.
        </p>
      )}
    </div>
  );
}
