import { Cpu, DollarSign, GitMerge } from 'lucide-react';

const features = [
  {
    title: 'Advanced AI Analysis',
    description: 'Powered by latest LLMs, we track data flows, identify bounded contexts, and find transactional boundaries.',
    icon: Cpu
  },
  {
    title: 'Cost Projections',
    description: 'Calculate exactly how much your new microservices architecture will cost to run on AWS or GCP.',
    icon: DollarSign
  },
  {
    title: 'Interactive Blueprints',
    description: 'Drag and drop service boundaries in a visual Neo4j graph before generating K8s manifests.',
    icon: GitMerge
  }
];

const Features = () => {
  return (
    <section className="py-24 border-t border-[#222] bg-[#0a0a0a]">
      <div className="container mx-auto px-4 max-w-5xl">
        <div className="mb-16">
          <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">Everything you need to transform</h2>
          <p className="text-gray-400 max-w-2xl">No more guessing. Get a mathematically and logically sound migration strategy.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {features.map((feature, idx) => {
            const IconComponent = feature.icon;
            return (
            <div key={idx} className="p-8 bg-[#111] border border-[#222] rounded-sm group hover:border-gray-500 transition-colors">
              <div className="mb-6 text-white group-hover:scale-105 transition-transform origin-left">
                <IconComponent className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">{feature.title}</h3>
              <p className="text-gray-400 text-sm leading-relaxed">{feature.description}</p>
            </div>
          )})}
        </div>
      </div>
    </section>
  );
};

export default Features;
