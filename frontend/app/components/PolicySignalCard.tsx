'use client';

import { motion } from 'framer-motion';
import { PolicySignal } from '../../core/models/PolicyContext';
import { useState } from 'react';

interface PolicySignalCardProps {
  signal: PolicySignal;
  onAcknowledge?: (id: string) => void;
}

export function PolicySignalCard({ signal, onAcknowledge }: PolicySignalCardProps) {
  const [expanded, setExpanded] = useState(false);

  // Type-based styling
  const getStyle = (type: string) => {
    switch (type) {
      case 'regulatory': return { border: '2px solid rgba(251, 146, 60, 0.5)', bg: 'rgba(40, 20, 10, 0.4)' }; // Orange tint
      case 'environmental': return { border: '2px solid rgba(74, 222, 128, 0.5)', bg: 'rgba(10, 40, 20, 0.4)' }; // Green tint
      default: return { border: '2px solid rgba(96, 165, 250, 0.5)', bg: 'rgba(10, 20, 40, 0.4)' }; // Blue tint (advisory)
    }
  };

  const style = getStyle(signal.boundaryType);

  return (
    <motion.div
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      className="policy-card"
      style={{
        borderLeft: style.border,
        padding: '0.5rem 0 0.5rem 0.8rem',
        marginBottom: '0.4rem',
        fontSize: '0.8rem',
        opacity: 0.8,
        transition: 'opacity 0.2s',
      }}
      onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
      onMouseLeave={(e) => e.currentTarget.style.opacity = '0.8'}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <div style={{ 
            fontSize: '0.75rem', 
            textTransform: 'uppercase', 
            opacity: 0.7, 
            marginBottom: '0.25rem',
            letterSpacing: '0.05em' 
          }}>
            {signal.boundaryType} Signal
          </div>
          <div style={{ fontWeight: 500, color: '#e0e0e0', marginBottom: '0.5rem' }}>
            {signal.message}
          </div>
        </div>
      </div>

      <div style={{ fontSize: '0.8rem', color: '#aaaaaa', marginTop: '0.5rem' }}>
        {signal.applicability}
      </div>

      {expanded && (
        <motion.div 
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          style={{ marginTop: '0.8rem', paddingTop: '0.8rem', borderTop: '1px solid rgba(255,255,255,0.1)' }}
        >
          <div style={{ marginBottom: '0.5rem' }}>
            <span style={{ color: '#888' }}>Reason:</span> {signal.reason}
          </div>
          {/* Learn More / Acknowledge area */}
          <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
            <button style={{ 
              background: 'transparent', border: 'none', color: '#60a5fa', cursor: 'pointer', padding: 0, fontSize: '0.85rem' 
            }}>
              Read Guidelines
            </button>
            {onAcknowledge && (
               <button 
                onClick={() => onAcknowledge(signal.id)}
                style={{ 
                  background: 'transparent', border: 'none', color: '#888', cursor: 'pointer', padding: 0, fontSize: '0.85rem' 
                }}
              >
               Dismiss
              </button>
            )}
          </div>
        </motion.div>
      )}

      <button 
        onClick={() => setExpanded(!expanded)}
        style={{ 
            background: 'transparent', 
            border: 'none', 
            color: '#888', 
            width: '100%',
            marginTop: '0.5rem',
            cursor: 'pointer',
            fontSize: '1.2rem',
            lineHeight: '0.5'
        }}
      >
        {expanded ? 'G' : '...'}
      </button>
    </motion.div>
  );
}
