"use client";

import {
  ResponsiveContainer,
  RadarChart as ReRadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
} from "recharts";

interface Trace {
  key: string;
  name: string;
  color: string;
  fill?: string;
  dash?: boolean;
}

interface RadarChartProps {
  data: Record<string, string | number>[];
  traces: Trace[];
  showLegend?: boolean;
}

export function RadarChart({ data, traces, showLegend = false }: RadarChartProps) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <ReRadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
        <PolarGrid stroke="rgba(26,20,16,0.20)" />
        <PolarAngleAxis
          dataKey="axis"
          tick={{
            fontFamily:
              "var(--font-ibm-plex-mono), 'IBM Plex Mono', ui-monospace, monospace",
            fontSize: 10,
            fill: "var(--color-ink, #1A1410)",
          }}
        />
        <PolarRadiusAxis
          domain={[0, 10]}
          tickCount={6}
          tick={{
            fontFamily:
              "var(--font-ibm-plex-mono), 'IBM Plex Mono', ui-monospace, monospace",
            fontSize: 9,
            fill: "var(--color-ink, #1A1410)",
          }}
          axisLine={false}
        />
        {traces.map((trace) => (
          <Radar
            key={trace.key}
            name={trace.name}
            dataKey={trace.key}
            stroke={trace.color}
            fill={trace.fill ?? "transparent"}
            fillOpacity={trace.fill ? 1 : 0}
            strokeWidth={trace.dash ? 1.5 : 2}
            strokeDasharray={trace.dash ? "5 5" : undefined}
            dot={false}
          />
        ))}
        {showLegend && (
          <Legend
            wrapperStyle={{
              fontFamily:
                "var(--font-ibm-plex-mono), 'IBM Plex Mono', ui-monospace, monospace",
              fontSize: 10,
            }}
          />
        )}
      </ReRadarChart>
    </ResponsiveContainer>
  );
}
