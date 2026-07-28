import { Link } from 'react-router-dom';
import { Copy } from 'lucide-react';

const Hero = () => {
  return (
    <section className="relative pt-12 pb-20 lg:pb-32">
      <div className="container mx-auto px-4 max-w-5xl">

        {/* Mock Navbar (matching the screenshot vibe) */}
        <div className="flex justify-between items-center mb-12 md:mb-24 pb-4 md:pb-8">
          <div className="text-2xl md:text-4xl font-logo tracking-widest text-gray-200">monomelt</div>
          <div className="hidden md:flex gap-8 text-sm text-gray-400">
            <span className="hover:text-white cursor-pointer transition-colors">GitHub</span>
            <span className="hover:text-white cursor-pointer transition-colors">Docs</span>
            <span className="hover:text-white cursor-pointer transition-colors">Data</span>
            <span className="hover:text-white cursor-pointer transition-colors">Zen</span>
            <span className="hover:text-white cursor-pointer transition-colors">Enterprise</span>
          </div>
          <Link to="/login" className="px-4 py-2 bg-white text-black font-bold text-sm rounded-sm hover:bg-gray-200 transition-colors flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            Try It
          </Link>
        </div>

        {/* Badge */}
        <div className="inline-block border border-[#222] bg-[#0a0a0a] text-gray-400 text-[10px] sm:text-xs mb-8 p-1 leading-relaxed">
          <span className="bg-white text-black px-2 py-0.5 mr-2 font-bold inline-block">New</span>
          <span>Introducing full AST parsing for legacy monoliths. <Link to="/login" className="text-gray-500 hover:text-white ml-1">Try it now</Link></span>
        </div>

        {/* Main Heading */}
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6 leading-tight">
          The open source AI <br className="hidden md:block" /> monolith deconstructor
        </h1>

        {/* Subtitle */}
        <p className="text-sm sm:text-base lg:text-lg text-gray-400 max-w-2xl mb-12 leading-relaxed">
          Upload your legacy codebase and let our AI agents analyze ASTs, identify bounded contexts, and generate production-ready microservices instantly.
        </p>

        {/* Terminal Box */}
        <div className="bg-[#111] border border-[#222] rounded-sm w-full max-w-3xl overflow-hidden">
          <div className="flex gap-4 md:gap-8 px-4 md:px-6 py-4 border-b border-[#222] text-xs md:text-sm font-bold overflow-x-auto whitespace-nowrap">
            <span className="text-white cursor-pointer">curl</span>
            <span className="text-gray-600 cursor-pointer hover:text-gray-400">npm</span>
            <span className="text-gray-600 cursor-pointer hover:text-gray-400">bun</span>
            <span className="text-gray-600 cursor-pointer hover:text-gray-400">brew</span>
            <span className="text-gray-600 cursor-pointer hover:text-gray-400">paru</span>
          </div>
          <div className="px-4 md:px-6 py-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 text-xs md:text-sm">
            <span className="text-gray-500 break-all sm:break-normal">curl -fsSL <span className="text-white font-bold">https://monomelt.ai/install</span> | bash</span>
            <Copy className="w-4 h-4 text-gray-600 hover:text-white cursor-pointer transition-colors self-end sm:self-auto shrink-0" />
          </div>
        </div>

      </div>
    </section>
  );
};

export default Hero;
