'use client';

import { useFarmStore } from '../../state/farmStore';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

export function FarmMap() {
  const { timeWindow } = useFarmStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Time-driven environmental drift (Task 3)
  // Maps timeWindow to visual parameters
  const lighting = {
    'today': { 
       shadowOpacity: 0.1, 
       shadowAngle: '45deg', 
       atmosTint: 'rgba(255,255,255,0)',
       soilTone: '#2a2a2a'
    },
    '7d': { 
       shadowOpacity: 0.2, 
       shadowAngle: '65deg', 
       atmosTint: 'rgba(255,240,200,0.05)', // Slight warm haze
       soilTone: '#282828'
    },
    '30d': { 
       shadowOpacity: 0.3, 
       shadowAngle: '85deg', 
       atmosTint: 'rgba(200,230,255,0.08)', // Cooler future haze
       soilTone: '#252525'
    },
    'season': {
        shadowOpacity: 0.4,
        shadowAngle: '100deg',
        atmosTint: 'rgba(200,220,255,0.1)',
        soilTone: '#222'
    },
    'multi-season': {
        shadowOpacity: 0.5,
        shadowAngle: '120deg',
        atmosTint: 'rgba(180,200,255,0.15)',
        soilTone: '#1a1a1a'
    }
  }[timeWindow] || { shadowOpacity: 0.1, shadowAngle: '45deg', atmosTint: 'transparent', soilTone: '#2a2a2a' };

  if (!mounted) return null;

  return (
    <div style={{
      position: 'absolute',
      top: 0,
      left: 0,
      width: '100%',
      height: '100%',
      zIndex: -1,
      overflow: 'hidden',
      background: '#111',
      pointerEvents: 'none' // Interactive elements overlay this
    }}>
      {/* 
        Task 1: Environmental Depth Layers 
        Bottom Layer: Soil / Base Landscape
      */}
      <div style={{
        position: 'absolute',
        inset: 0,
         // Subtle gradients, no flat colors
        background: `radial-gradient(circle at 50% 50%, ${lighting.soilTone}, #111)`,
        transition: 'background 1s cubic-bezier(0.2, 0.8, 0.2, 1)' // Delayed Intentionality base
      }} />

      {/* Surface Pattern Variation (Noise / Texture) */}
      <div style={{
          position: 'absolute',
          inset: 0,
          opacity: 0.03,
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
          pointerEvents: 'none'
      }} />

      {/* 
        Task 2: "Surveyed" Field Boundaries 
        Using SVG with imperfect paths
      */}
      <svg width="100%" height="100%" style={{ position: 'absolute', top: 0, left: 0 }}>
        <defs>
            <filter id="irregular-edge">
                <feTurbulence type="fractalNoise" baseFrequency="0.05" numOctaves="2" result="noise" />
                <feDisplacementMap in="SourceGraphic" in2="noise" scale="3" />
            </filter>
            <filter id="soft-glow">
                <feGaussianBlur stdDeviation="5" result="coloredBlur" />
                <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                </feMerge>
            </filter>
        </defs>

        {/* Field A: Maize - Active */}
        <motion.path
            // Irregular polygon, not a rect
            d="M 150,200 C 350,180 600,210 800,200 L 780,500 C 500,520 200,510 160,480 Z"
            fill="transparent"
            stroke="rgba(74, 222, 128, 0.3)" // Green-400
            strokeWidth="2"
            filter="url(#irregular-edge)"
            initial={{ opacity: 0 }}
            animate={{ 
                opacity: 1,
                fill: 'rgba(74, 222, 128, 0.05)',
                filter: 'url(#irregular-edge)'
            }}
            transition={{ 
                duration: 2, 
                delay: 0.2, // Delayed Intentionality
                ease: [0.22, 1, 0.36, 1] // Custom refined ease
            }}
        />
        
        {/* Field B: Fallow/Planning */}
        <motion.path
            d="M 850,220 L 1150,230 L 1120,480 L 830,460 Z"
            fill="transparent"
            stroke="rgba(148, 163, 184, 0.3)" // Slate-400
            strokeWidth="1.5"
            filter="url(#irregular-edge)"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, fill: 'rgba(148, 163, 184, 0.03)' }}
            transition={{ duration: 2.5, delay: 0.4, ease: [0.22, 1, 0.36, 1] }}
        />

        {/* 
          Task 12: Historical Memory Traces 
          "Ghost" of previous season's boundary or yield map. 
          Static, faint, suggests "The farm remembers".
        */}
        <path
            d="M 160,210 C 340,200 610,220 790,210 L 770,510 C 510,515 210,500 170,490 Z"
            fill="transparent"
            stroke="rgba(255, 255, 255, 0.05)"
            strokeWidth="1"
            strokeDasharray="4 4"
            style={{ 
                pointerEvents: 'none',
                filter: 'blur(0.5px)' 
            }}
        />

        {/* 
          Task 3: Time-Driven Environmental Drift 
          Shadows/Clouds overlay that shifts based on timeWindow
        */}
        <motion.g
            animate={{
                x: timeWindow === '7d' ? 50 : timeWindow === '30d' ? 100 : 0,
                opacity: lighting.shadowOpacity
            }}
            transition={{ duration: 4, ease: "easeInOut" }} // Slow, deep time feel
        >
             {/* Abstract Cloud Shadows */}
             <path d="M 0,0 Q 400,100 800,0 T 1600,0" stroke="none" fill="rgba(0,0,0,0.3)" filter="url(#soft-glow)" transform="scale(2)" />
        </motion.g>

      </svg>

      {/* Task 1: Atmosphere Top Layer */}
      <motion.div 
        animate={{ backgroundColor: lighting.atmosTint }}
        transition={{ duration: 3 }}
        style={{
            position: 'absolute',
            inset: 0,
            pointerEvents: 'none',
            backdropFilter: 'blur(2px)', // Minimal blur for depth
            maskImage: 'linear-gradient(to bottom, transparent 40%, black 100%)' // Fog accumulates at bottom
        }}
      />
    </div>
  );
}
