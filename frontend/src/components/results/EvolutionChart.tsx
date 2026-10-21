import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { GenerationHistoryPoint } from '../../types/research';
import { formatCompact, formatScore } from '../../lib/format';

const AXIS_TICK = { fill: 'var(--text-dim)', fontSize: 11 };

export default function EvolutionChart({ data }: { data: GenerationHistoryPoint[] }) {
  if (!data.length) return null;

  return (
    <div className="evolution-chart">
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 36, right: 16, bottom: 12, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
          <XAxis
            dataKey="generation"
            allowDecimals={false}
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={{ stroke: 'var(--line)' }}
            label={{ value: 'Generation', position: 'insideBottom', offset: -6, fill: 'var(--text-dim)', fontSize: 11 }}
          />
          <YAxis
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={false}
            width={56}
            tickFormatter={(value: number) => formatCompact(value)}
          />
          <Tooltip
            contentStyle={{ background: 'var(--surface-raised)', border: '1px solid var(--line)', borderRadius: 6 }}
            labelFormatter={(generation) => `Generation ${generation}`}
            formatter={(value) => formatScore(Number(value))}
          />
          <Legend verticalAlign="top" align="right" wrapperStyle={{ fontSize: '0.75rem', paddingBottom: 12 }} />
          <Line type="monotone" dataKey="best_score" name="Best score" stroke="var(--brass-bright)" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="average_score" name="Average score" stroke="var(--moss-light)" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
