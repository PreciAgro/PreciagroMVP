'use client';

import { useAlertStore } from '../../../state/useAlertStore';
import { useWorkflowStore } from '../../../state/useWorkflowStore';
import { motion, AnimatePresence } from 'framer-motion';

import { useOutcomeTracker } from '../../../state/useOutcomeTracker';

export function EmergencyOverlay() {
  const { activeEmergency, acknowledgeEmergency } = useAlertStore();
  const { startWorkflow } = useWorkflowStore();
  const { trackCompletion } = useOutcomeTracker();

  // If no emergency or already acknowledged, don't show overlay
  if (!activeEmergency || activeEmergency.state !== 'active') return null;

  const handleAcknowledge = () => {
      // 1. Acknowledge the alert (hides this overlay)
      acknowledgeEmergency();
      // 2. Attempt to start guidance
      if (activeEmergency) {
          trackCompletion(activeEmergency.id, 'emergency-overlay');
          startWorkflow(activeEmergency.id);
      }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          backgroundColor: 'rgba(50, 0, 0, 0.96)', // Deep red, high opacity
          zIndex: 9999, // TOP PRIORITY
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '2rem',
          color: '#fff',
          textAlign: 'center'
        }}
      >
        {/* Pulsing Warning Icon */}
        <motion.div
            animate={{ scale: [1, 1.2, 1], opacity: [1, 0.8, 1] }}
            transition={{ repeat: Infinity, duration: 1.5 }}
            style={{ 
                fontSize: '4rem', 
                marginBottom: '1.5rem',
                filter: 'drop-shadow(0 0 20px rgba(255,0,0,0.8))'
            }}
        >
            🚨
        </motion.div>

        <h1 style={{ 
            fontSize: '2rem', 
            fontWeight: 800, 
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
            marginBottom: '1rem',
            color: '#fee2e2'
        }}>
            Critical Alert
        </h1>

        <div style={{ maxWidth: '400px', marginBottom: '2.5rem' }}>
            <p style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem' }}>
                {activeEmergency.message}
            </p>
            <p style={{ fontSize: '1rem', opacity: 0.8, marginBottom: '1.5rem' }}>
                Risk if ignored: {activeEmergency.consequenceIfIgnored}
            </p>
            
            <div style={{ 
                border: '1px solid rgba(255,255,255,0.3)', 
                padding: '1rem', 
                borderRadius: '8px',
                backgroundColor: 'rgba(0,0,0,0.3)' 
            }}>
                <div style={{ fontSize: '0.85rem', textTransform: 'uppercase', opacity: 0.7, marginBottom: '0.25rem' }}>
                    Recommended Action
                </div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fca5a5' }}>
                    {activeEmergency.recommendedAction}
                </div>
            </div>
        </div>

        {/* Action Button */}
        <button
            onClick={handleAcknowledge}
            style={{
                background: '#fff',
                color: '#991b1b', // Red-800
                border: 'none',
                padding: '1rem 3rem',
                fontSize: '1.1rem',
                fontWeight: 700,
                borderRadius: '50px',
                cursor: 'pointer',
                boxShadow: '0 0 20px rgba(255,255,255,0.4)',
                transition: 'transform 0.2s'
            }}
            onMouseOver={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
            onMouseOut={(e) => e.currentTarget.style.transform = 'scale(1)'}
        >
            Acknowledge & Act
        </button>

        {activeEmergency.externalChannels && activeEmergency.externalChannels.length > 0 && (
            <div style={{ marginTop: '2rem', opacity: 0.5, fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span>📱 Sent via WhatsApp</span>
            </div>
        )}

      </motion.div>
    </AnimatePresence>
  );
}
