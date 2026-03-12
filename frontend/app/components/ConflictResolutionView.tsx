'use client';

import { PolicyConflict } from '../../core/models/PolicyContext';
import { motion } from 'framer-motion';

interface ConflictResolutionViewProps {
  conflict: PolicyConflict;
}

export function ConflictResolutionView({ conflict }: ConflictResolutionViewProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      style={{
        padding: '1.5rem',
        backgroundColor: 'rgba(30, 30, 30, 0.95)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '8px',
        margin: '1rem 0'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', marginBottom: '1rem' }}>
        <span style={{ fontSize: '1.5rem' }}>⚖️</span>
        <div>
           <h3 style={{ margin: 0, fontSize: '1rem', color: '#fff' }}>Decision Context</h3>
           <p style={{ margin: 0, fontSize: '0.85rem', color: '#aaa' }}>{conflict.description}</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1px 1fr', gap: '1rem', alignItems: 'stretch' }}>
          {/* Option A: Farmer Goal */}
          <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '4px' }}>
              <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: '#fff' }}>
                  Path A: {conflict.farmerGoal || 'Current Plan'}
              </h4>
              <p style={{ fontSize: '0.8rem', color: '#ccc', lineHeight: '1.4' }}>
                  {conflict.tradeoff.chooseFarmerGoal}
              </p>
          </div>

          {/* Divider */}
          <div style={{ background: 'rgba(255,255,255,0.1)' }} />

          {/* Option B: Policy Alignment */}
          <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '4px' }}>
             <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: '#fff' }}>
                  Path B: Policy Alignment
              </h4>
              <p style={{ fontSize: '0.8rem', color: '#ccc', lineHeight: '1.4' }}>
                  {conflict.tradeoff.choosePolicy}
              </p>
          </div>
      </div>

      <div style={{ marginTop: '1rem', fontSize: '0.8rem', color: '#666', fontStyle: 'italic', textAlign: 'center' }}>
          System advises consideration. Choice remains with you.
      </div>
    </motion.div>
  );
}
