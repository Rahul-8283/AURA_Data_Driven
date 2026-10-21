import { motion } from 'framer-motion';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import type { MaterialCandidate } from '../../types/research';
import { NMC811_BASELINE } from '../../lib/baseline';
import { formatScore } from '../../lib/format';
import FormulaText from './FormulaText';

const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

function buildRadarData(material: MaterialCandidate) {
  const safeCost = material.cost_estimate_usd_kg > 0 ? material.cost_estimate_usd_kg : 0.01;
  return [
    { metric: 'Capacity', value: (material.specific_capacity / NMC811_BASELINE.specific_capacity) * 100 },
    { metric: 'Voltage', value: (material.voltage / NMC811_BASELINE.voltage) * 100 },
    { metric: 'Cycle life', value: (material.cycle_life / NMC811_BASELINE.cycle_life) * 100 },
    { metric: 'Cost', value: (NMC811_BASELINE.cost_estimate_usd_kg / safeCost) * 100 },
  ];
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="material-card__stat">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export default function MaterialCard({ material, rank }: { material: MaterialCandidate; rank: number }) {
  return (
    <motion.article className="material-card" variants={cardVariants}>
      <header className="material-card__top">
        <span className="material-card__rank">{rank}</span>
        <h3 className="material-card__formula">
          <FormulaText formula={material.composition} />
        </h3>
        <span
          className="material-card__score"
          title="Score = capacity × voltage × cycle life ÷ cost, reduced for each target the material misses"
        >
          Score {formatScore(material.fitness)}
        </span>
      </header>

      <div className="material-card__body">
        <dl className="material-card__stats">
          <Stat label="Capacity" value={`${Math.round(material.specific_capacity)} mAh/g`} />
          <Stat label="Voltage" value={`${material.voltage.toFixed(2)} V`} />
          <Stat label="Cycle life" value={`${formatScore(material.cycle_life)} cycles`} />
          <Stat label="Cost" value={`$${material.cost_estimate_usd_kg.toFixed(2)}/kg`} />
        </dl>

        <div className="material-card__radar" aria-label="Comparison with the NMC811 baseline">
          <ResponsiveContainer width="100%" height={170}>
            <RadarChart data={buildRadarData(material)} outerRadius="68%">
              <PolarGrid stroke="var(--line)" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: 'var(--text-dim)', fontSize: 10 }} />
              <PolarRadiusAxis angle={90} domain={[0, 150]} tick={false} axisLine={false} />
              <Radar name={material.composition} dataKey="value" stroke="var(--brass-bright)" fill="var(--brass)" fillOpacity={0.3} />
            </RadarChart>
          </ResponsiveContainer>
          <small>Outer ring = NMC811 baseline</small>
        </div>
      </div>

      {material.reasoning && (
        <details className="material-card__details">
          <summary>Why this material</summary>
          <p>{material.reasoning}</p>
        </details>
      )}
    </motion.article>
  );
}
