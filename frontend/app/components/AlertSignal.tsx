'use client';

import { motion, Variants } from 'framer-motion';
import { Alert, EscalationLevel } from '../../core/models/Alert';
import { useEffect } from 'react';

interface AlertSignalProps {
  alert: Alert;
  className?: string; // Allow positioning overrides
}

export function AlertSignal({ alert, className = '' }: AlertSignalProps) {
  // Escalation Level Visuals
  // L0: Invisible/Passive (Render nothing or minimal dot?) -> Logic says "Passive Signal", Insight exists quietly. Maybe just a color accent in InsightCard, handled there. 
  //     But if this component is used, it might be for explicit signals.
  //     Let's treat L0 as "no additional signal icon/pulse", just the base UI.
  
  if (alert.escalationLevel === 0) return null;

  // Colors based on Severity (Strictly controlled)
  const getSignalColor = () => {
    if (alert.severity === 'critical') return '#ef4444'; // Red-500
    if (alert.severity === 'high') return '#f97316'; // Orange-500
    if (alert.severity === 'medium') return '#eab308'; // Yellow-500
    return '#3b82f6'; // Blue-500 (Low)
  };

  const color = getSignalColor();

  // Motion Configuration (Level 2+)
  const isMotionActive = alert.escalationLevel >= 2;
  const isEmergency = alert.escalationLevel === 3;
  
  const pulseVariant: Variants = {
    initial: { scale: 1, opacity: 0.8 },
    animate: { 
      scale: isEmergency ? [1, 1.5, 1] : [1, 1.2, 1], // Aggressive pulse for emergency
      opacity: isEmergency ? [0.8, 0, 0.8] : [0.8, 0.4, 0.8],
      transition: { 
        duration: isEmergency ? 1 : 3, // Fast vs Slow
        repeat: Infinity,
        ease: "easeInOut" 
      }
    }
  };

  // Task 8: Gravitational Attention
  // If Alert is critical/L3, dim the world.
  useEffect(() => {
    if (alert.severity === 'critical' || alert.escalationLevel === 3) {
      document.body.setAttribute('data-attention-mode', 'gravitational');
    } else {
      // Only remove if we are the one who set it (simplified: remove if WE are not critical)
      // Ideally this should be in a store or context to handle multiple alerts, 
      // but for Phase 4 single-object view, this works.
      // Better safety: check if any other critical alert exists? 
      // Current scope: We assume one primary view context.
      document.body.removeAttribute('data-attention-mode');
    }

    return () => {
       document.body.removeAttribute('data-attention-mode');
    };
  }, [alert.severity, alert.escalationLevel]);

  return (
    <div className={className} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        {/* External Channel Icon */}
        {(alert as any).externalChannels?.length > 0 && (
            <span style={{ fontSize: '1rem' }} title="Sent via External Channel">📲</span>
        )}

        {/* The Signal Orb */}
        <div style={{ position: 'relative', width: '10px', height: '10px' }}>
            {isMotionActive && (
                <motion.div
                    variants={pulseVariant}
                    initial="initial"
                    animate="animate"
                    style={{
                        position: 'absolute',
                        top: 0, left: 0,
                        width: '100%', height: '100%',
                        borderRadius: '50%',
                        backgroundColor: color,
                    }}
                />
            )}
            <div 
                style={{
                    width: '100%', height: '100%',
                    borderRadius: '50%',
                    backgroundColor: color,
                    boxShadow: alert.escalationLevel >= 1 ? `0 0 4px ${color}` : 'none'
                }} 
            />
        </div>
        
        {/* Optional Label for Accessibility/Clarity if needed, mainly for debugging or specific layouts */}
        {/* Phase 4 doctrine: "Alerts are states of risk attached to an object". The Object/Insight Card carries the text. 
            This component is purely the "Signal" visualizer. */}
    </div>
  );
}
