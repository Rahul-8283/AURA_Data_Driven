import { Link } from 'react-router-dom';

const CallToAction = () => {
  return (
    <section className="py-24 border-t border-[#222] bg-[#0a0a0a]">
      <div className="container mx-auto px-4 max-w-5xl">
        <div className="bg-[#111] border border-[#222] p-12 rounded-sm text-center">
          <h2 className="text-3xl font-bold text-white mb-4">Ready to break the monolith?</h2>
          <p className="text-base text-gray-400 mb-10 max-w-2xl mx-auto">
            Stop debating architecture in endless meetings. Let AI give you the data-driven blueprint you need today.
          </p>
          <Link to="/login" className="inline-block px-8 py-3 bg-white text-black hover:bg-gray-200 font-bold rounded-sm transition-colors text-sm">
            Start Your Transformation Free
          </Link>
        </div>
      </div>
    </section>
  );
};

export default CallToAction;
