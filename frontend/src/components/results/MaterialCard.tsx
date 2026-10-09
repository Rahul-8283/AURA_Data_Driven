import { motion } from 'framer-motion';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import type { MaterialCandidate } from '../../types/research';
import { NMC811_BASELINE } from '../../lib/baseline';

const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

function buildRadarData(material: MaterialCandidate) {
  const safeCost = material.cost_estimate_usd_kg > 0 ? material.cost_estimate_usd_kg : 0.01;
  return [
    { metric: 'Capacity', value: (material.specific_capacity / NMC811_BASELINE.specific_capacity) * 100 },
    { metric: 'Voltage', value: (material.voltage / NMC811_BASELINE.voltage) * 100 },
    { metric: 'Cycle Life', value: (material.cycle_life / NMC811_BASELINE.cycle_life) * 100 },
    { metric: 'Cost Efficiency', value: (NMC811_BASELINE.cost_estimate_usd_kg / safeCost) * 100 },
  ];
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="material-card__stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default function MaterialCard({ material, rank }: { material: MaterialCandidate; rank: number }) {
  const radarData = buildRadarData(material);

  return (
    <motion.div className="material-card" variants={cardVariants}>
      <div className="material-card__header">
        <span className="material-card__rank">#{rank}</span>
        <strong className="material-card__formula">{material.composition}</strong>
      </div>

      <div className="material-card__body">
        <div className="material-card__stats">
          <Stat label="Capacity" value={`${material.specific_capacity} mAh/g`} />
          <Stat label="Voltage" value={`${material.voltage} V`} />
          <Stat label="Cycle Life" value={`${material.cycle_life}`} />
          <Stat label="Cost" value={`$${material.cost_estimate_usd_kg}/kg`} />
          <Stat label="Fitness" value={material.fitness.toFixed(2)} />
        </div>

        <div className="material-card__radar">
          <ResponsiveContainer width="100%" height={180}>
            <RadarChart data={radarData} outerRadius="75%">
              <PolarGrid stroke="var(--line)" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: 'var(--text-dim)', fontSize: 10 }} />
              <PolarRadiusAxis angle={30} domain={[0, 150]} tick={false} axisLine={false} />
              <Radar
                name={material.composition}
                dataKey="value"
                stroke="var(--brass-bright)"
                fill="var(--brass)"
                fillOpacity={0.35}
              />
            </RadarChart>
          </ResponsiveContainer>
          <small className="material-card__radar-caption">vs. NMC811 baseline (100% ring)</small>
        </div>
      </div>

      <p className="material-card__reasoning">{material.reasoning}</p>
    </motion.div>
  );
}
