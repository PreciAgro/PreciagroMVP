'use client';

import { usePolicyStore } from '../../state/usePolicyStore';
import { motion } from 'framer-motion';

export function SystemAwarenessPanel() {
  const { systemAwarenessSignals, resourceConstraints } = usePolicyStore();

  if (systemAwarenessSignals.length === 0 && resourceConstraints.length === 0) {
    return null;
  }

  return (
    <section
      aria-label="Regional context signals"
      style={{
        marginBottom: 'var(--space-4)',
        padding: 'var(--space-3)',
        borderTop: '1px solid var(--color-border)',
        borderBottom: '1px solid var(--color-border)'
      }}
    >
      <h2 style={{
        fontSize: 'var(--font-size-xs)',
        textTransform: 'uppercase',
        letterSpacing: 'var(--letter-spacing-wide)',
        color: 'var(--color-text-tertiary)',
        marginBottom: 'var(--space-3)',
        fontWeight: 600
      }}>
        Regional Context
      </h2>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        {systemAwarenessSignals.map((signal, idx) => (
          <motion.div 
            key={`sys-${idx}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: idx * 0.1 }}
            style={{
              display: 'flex',
              gap: 'var(--space-2)',
              alignItems: 'center',
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-text-secondary)'
            }}
          >
            <span style={{ fontSize: 'var(--font-size-lg)' }} aria-hidden="true">🌍</span>
            <div>
              <div style={{ fontWeight: 500, color: 'var(--color-text-primary)' }}>
                {signal.metric}: {signal.trend}
              </div>
              <div style={{
                fontSize: 'var(--font-size-xs)',
                color: 'var(--color-text-tertiary)',
                marginTop: 'var(--space-0-5)'
              }}>
                {signal.relevance}
              </div>
            </div>
          </motion.div>
        ))}

        {resourceConstraints.map((constraint, idx) => (
          <motion.div 
            key={`res-${idx}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: (systemAwarenessSignals.length + idx) * 0.1 }}
            style={{
              display: 'flex',
              gap: 'var(--space-2)',
              alignItems: 'center',
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-text-secondary)'
            }}
          >
            <span style={{ fontSize: 'var(--font-size-lg)' }} aria-hidden="true">💧</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 500, color: 'var(--color-text-primary)' }}>
                {constraint.type}: {constraint.trend}
              </div>
              <div
                role="progressbar"
                aria-valuenow={constraint.currentLevel}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${constraint.type} level at ${constraint.currentLevel}%`}
                style={{ 
                  width: '100px',
                  height: '4px',
                  background: 'var(--color-border)',
                  borderRadius: '2px',
                  marginTop: 'var(--space-1)',
                  overflow: 'hidden'
                }}
              >
                <div style={{ 
                  width: `${constraint.currentLevel}%`,
                  height: '100%',
                  background: constraint.currentLevel < constraint.threshold
                    ? 'var(--color-danger)'
                    : 'var(--color-success)',
                  transition: `width var(--duration-medium) var(--ease-standard)`
                }} />
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
