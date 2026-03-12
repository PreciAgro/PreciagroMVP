'use client';

import { useState, useEffect } from 'react';
import { useFarmStore } from '../../state/farmStore';
import { useAlertStore } from '../../state/useAlertStore';

export function DemoControls() {
  const [visible, setVisible] = useState(false);
  const { setScenario, setTimeWindow, selectObject } = useFarmStore();
  const { resolveEmergency, activeEmergency } = useAlertStore();

  // Task 15: Hidden Investor Mode Trigger (Ctrl+Shift+D)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        setVisible(v => !v);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (!visible) return (
      // Hidden click area top-left as backup
      <div 
        onClick={() => setVisible(true)}
        style={{ position: 'fixed', top: 0, left: 0, width: '20px', height: '20px', zIndex: 9999, cursor: 'default' }} 
      />
  );

  const handleScenario = (type: 'calm' | 'risk' | 'emergency') => {
      console.log("Forcing Scenario:", type);
      
      // Reset first
      if (activeEmergency) resolveEmergency();
      setScenario(null); 
      setTimeWindow('today');

      setTimeout(() => {
          switch(type) {
              case 'calm':
                  setScenario('healthy');
                  selectObject({ id: 'field-a', name: 'Maize Field A', type: 'field' });
                  break;
              case 'risk':
                  setScenario('demo_fungal_risk');
                  setTimeWindow('7d');
                  selectObject({ id: 'field-a', name: 'Maize Field A', type: 'field' });
                  break;
              case 'emergency':
                  setScenario('demo_drought_stress');
                  setTimeWindow('30d');
                  selectObject({ id: 'field-a', name: 'Maize Field A', type: 'field' });
                  break;
          }
      }, 500); // Wait for reset
  };

  return (
    <aside
      role="complementary"
      aria-label="Demo controls"
      style={{
        position: 'fixed',
        bottom: 'var(--space-4)',
        right: 'var(--space-4)',
        background: 'rgba(22, 22, 22, 0.95)',
        backdropFilter: 'blur(20px) saturate(180%)',
        border: '1px solid var(--color-border)',
        borderRadius: '12px',
        padding: 'var(--space-4)',
        zIndex: 10000,
        color: 'var(--color-text-primary)',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
        minWidth: '280px',
        transition: `transform var(--duration-medium) var(--ease-out-expo), opacity var(--duration-medium) var(--ease-out-expo)`
      }}
    >
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 'var(--space-3)'
      }}>
        <h2 style={{
          margin: 0,
          fontSize: 'var(--font-size-xs)',
          color: 'var(--color-text-tertiary)',
          textTransform: 'uppercase',
          letterSpacing: 'var(--letter-spacing-wide)',
          fontWeight: 600
        }}>
          Demo Control
        </h2>
        <button
          onClick={() => setVisible(false)}
          aria-label="Close demo controls"
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--color-text-tertiary)',
            cursor: 'pointer',
            padding: 'var(--space-1)',
            fontSize: 'var(--font-size-base)',
            transition: `color var(--duration-micro) var(--ease-standard)`
          }}
          onMouseEnter={(e) => e.currentTarget.style.color = 'var(--color-text-primary)'}
          onMouseLeave={(e) => e.currentTarget.style.color = 'var(--color-text-tertiary)'}
        >
          ✕
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
        <button 
          onClick={() => handleScenario('calm')}
          aria-label="Activate calm scenario"
          style={{
            ...btnStyle,
            borderLeft: '3px solid var(--color-success)'
          }}
        >
          <span style={{ fontSize: 'var(--font-size-sm)' }}>1. Calm / Healthy</span>
        </button>
        
        <button 
          onClick={() => handleScenario('risk')}
          aria-label="Activate risk scenario"
          style={{
            ...btnStyle,
            borderLeft: '3px solid var(--color-warning)'
          }}
        >
          <span style={{ fontSize: 'var(--font-size-sm)' }}>2. Emerging Risk</span>
        </button>
        
        <button 
          onClick={() => handleScenario('emergency')}
          aria-label="Activate emergency scenario"
          style={{
            ...btnStyle,
            borderLeft: '3px solid var(--color-danger)'
          }}
        >
          <span style={{ fontSize: 'var(--font-size-sm)' }}>3. Emergency</span>
        </button>
        
        <button 
          onClick={() => { setScenario(null); setTimeWindow('today'); }}
          aria-label="Reset all scenarios"
          style={{
            ...btnStyle,
            marginTop: 'var(--space-2)',
            opacity: 0.5
          }}
        >
          <span style={{ fontSize: 'var(--font-size-sm)' }}>Reset All</span>
        </button>
      </div>
      
      <div style={{
        marginTop: 'var(--space-4)',
        paddingTop: 'var(--space-3)',
        borderTop: '1px solid var(--color-border)',
        fontSize: 'var(--font-size-xs)',
        color: 'var(--color-text-tertiary)',
        textAlign: 'center'
      }}>
        PreciAgro Investor Build v10.0
      </div>
    </aside>
  );
}

const btnStyle: React.CSSProperties = {
  background: 'var(--color-overlay)',
  border: '1px solid var(--color-border)',
  padding: 'var(--space-2) var(--space-3)',
  borderRadius: '6px',
  color: 'var(--color-text-primary)',
  fontSize: 'var(--font-size-sm)',
  cursor: 'pointer',
  textAlign: 'left',
  transition: `all var(--duration-small) var(--ease-standard)`,
  fontFamily: 'var(--font-family)',
  fontWeight: 500,
  display: 'flex',
  alignItems: 'center',
};
