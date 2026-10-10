import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { GenerationHistoryPoint } from '../../types/research';

export default function EvolutionChart({ data }: { data: GenerationHistoryPoint[] }) {
  if (!data.length) return null;

  return (
    <div className="evolution-chart">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
          <XAxis
            dataKey="generation"
            tick={{ fill: 'var(--text-dim)', fontSize: 11 }}
            label={{ value: 'Generation', position: 'insideBottom', offset: -5, fill: 'var(--text-dim)' }}
          />
          <YAxis tick={{ fill: 'var(--text-dim)', fontSize: 11 }} />
          <Tooltip contentStyle={{ background: 'var(--surface-raised)', border: '1px solid var(--line)', borderRadius: 8 }} />
          <Legend wrapperStyle={{ fontSize: '0.75rem' }} />
          <Line type="monotone" dataKey="best_score" name="Best Score" stroke="var(--brass-bright)" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="average_score" name="Average Score" stroke="var(--moss-light)" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
