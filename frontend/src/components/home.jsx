import { Link } from 'react-router-dom'
import { Activity, Shield, Zap, ArrowRight } from 'lucide-react'
import Antigravity from './Antigravity';

export default function Home() {
  return (
    <div className="relative w-full min-h-screen">
      {/* <div className="absolute inset-0 z-0">
        <Antigravity
          count={300}
          magnetRadius={14}
          ringRadius={6}
          waveSpeed={0.4}
          waveAmplitude={1}
          particleSize={1.3}
          lerpSpeed={0.05}
          color="#5227FF"
          autoAnimate
          particleVariance={1}
          rotationSpeed={0}
          depthFactor={1}
          pulseSpeed={3}
          particleShape="capsule"
          fieldStrength={10}
        />
      </div> */}
      <div className="relative z-10 min-h-screen bg-transparent flex flex-col font-sans">
      <nav className="h-16 px-8 flex items-center justify-between bg-white border-b border-[#E5E5E5] sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <img src="/Xone.png" alt="XOne Logo" className="w-8 h-8 object-contain" />
          <span className="font-bold text-lg tracking-tight text-[#171717]">XOne</span>
        </div>
        <div className="flex items-center gap-4">
          <Link 
            to="/auth" 
            className="text-sm font-medium text-[#737373] hover:text-[#171717] transition-colors"
          >
            Login
          </Link>
          <Link 
            to="/auth" 
            className="bg-[#171717] text-white text-sm font-medium px-4 py-2 rounded shadow hover:bg-black transition-colors"
          >
            Sign Up
          </Link>
        </div>
      </nav>

      <main className="flex-1 flex flex-col items-center justify-center -mt-16 px-4">
        <div className="max-w-3xl text-center space-y-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-black/5 text-sm font-medium text-[#171717]">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            System is operational
          </div>
          
          <h1 className="text-5xl md:text-7xl font-extrabold text-[#171717] tracking-tighter leading-tight drop-shadow-sm">
            Detect,Diagnose and Deploy Fixes
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-gray-500">
              before the pager even rings
            </span>
          </h1>
          
          <p className="text-lg text-[#737373] max-w-2xl mx-auto font-light">
            Keep your critical systems running smoothly with intelligent, automated patching and recovery. Zero downtime. Zero hassle.
          </p>
          
          <div className="flex items-center justify-center pt-4">
            <Link 
              to="/auth" 
              className="group flex items-center gap-2 bg-[#171717] text-white px-8 py-4 rounded-lg font-medium shadow-lg hover:bg-black transition-all hover:scale-105 active:scale-95"
            >
              Get Started
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-5xl w-full mt-24">
          <div className="bg-white p-6 rounded-xl border border-[#E5E5E5] shadow-sm flex flex-col items-center text-center">
            <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-4">
              <Zap className="w-6 h-6 text-[#171717]" />
            </div>
            <h3 className="font-semibold text-lg text-[#171717] mb-2">Automated Patching</h3>
            <p className="text-sm text-[#737373]">Instantly detect and resolve vulnerabilities without manual intervention.</p>
          </div>
          <div className="bg-white p-6 rounded-xl border border-[#E5E5E5] shadow-sm flex flex-col items-center text-center">
            <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-4">
              <Shield className="w-6 h-6 text-[#171717]" />
            </div>
            <h3 className="font-semibold text-lg text-[#171717] mb-2">Bulletproof Security</h3>
            <p className="text-sm text-[#737373]">Ensure your infrastructure is always up-to-date with top-tier security standards.</p>
          </div>
          <div className="bg-white p-6 rounded-xl border border-[#E5E5E5] shadow-sm flex flex-col items-center text-center">
            <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-4">
              <Activity className="w-6 h-6 text-[#171717]" />
            </div>
            <h3 className="font-semibold text-lg text-[#171717] mb-2">Zero Downtime</h3>
            <p className="text-sm text-[#737373]">Seamless fault recovery operations configured to keep your services online.</p>
          </div>
        </div>
      </main>
      
      <footer className="py-8 text-center text-[#737373] text-sm border-t border-[#E5E5E5]">
        © {new Date().getFullYear()} XOne Inc. Built for continuous uptime.
      </footer>
    </div>
    </div>
  )
}
