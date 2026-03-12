'use client';

import { motion } from 'framer-motion';
import { Insight } from '../../core/models/Insight';
import { Alert } from '../../core/models/Alert';
import { AlertSignal } from './AlertSignal';
import { useOutcomeTracker } from '../../state/useOutcomeTracker';
import { useLearningStore } from '../../state/useLearningStore';
import { usePolicyStore } from '../../state/usePolicyStore';
import { PolicySignalCard } from './PolicySignalCard';
import { useState } from 'react';

interface InsightCardProps {
  insight: Insight;
  alert?: Alert;
}

export function InsightCard({ insight, alert }: InsightCardProps) {
  const { trackDismissal, trackPositiveFeedback } = useOutcomeTracker();
  const getExplanation = useLearningStore(s => s.getExplanation);
  const getRelevantPolicies = usePolicyStore(s => s.getPolicyForAction);
  const [isDismissed, setIsDismissed] = useState(false);

  // Transparency: Why did this adapt?
  const transparencyExplanation = getExplanation(insight.id);
  
  // Phase 10: Check for relevant policies
  const relevantPolicies = getRelevantPolicies(insight.type); // Simplified mapping for now

  const handleDismiss = (e: React.MouseEvent) => {
    e.stopPropagation();
    trackDismissal(insight.id, 'insight-card');
    setIsDismissed(true);
  };

  const handleHelpful = (e: React.MouseEvent) => {
    e.stopPropagation();
    trackPositiveFeedback(insight.id, 'insight-card');
    // Visual feedback could be added here
  };

  if (isDismissed) return null;

  // Visual Hierarchy Logic:
  // IF Alert exists, it overrides default Insight styling based on Escalation Level.
  // ELSE, fallback to Insight.level.

  // Determine Effective Severity for color logic
  const severity = alert ? alert.severity : insight.level;
  
  // Base Colors
  const getColor = (s: string) => {
    switch (s) {
      case 'critical': return 'rgba(248, 113, 113, 1)'; // Red-400
      case 'high': case 'warning': return 'rgba(250, 204, 21, 1)'; // Yellow-400
      case 'medium': return 'rgba(251, 146, 60, 1)'; // Orange-400
      case 'low': case 'info': return 'rgba(96, 165, 250, 1)'; // Blue-400
      case 'success': return 'rgba(74, 222, 128, 1)'; // Green-400
      default: return 'rgba(156, 163, 175, 1)'; // Gray-400
    }
  };

  const baseColor = getColor(severity);
  const escalationLevel = alert?.escalationLevel ?? 0;

  // Level 1+: Border Emphasis
  const borderStyle = escalationLevel >= 1 
    ? `3px solid ${baseColor}`
    : `3px solid ${baseColor.replace('1)', '0.4)')}`;

  // Level 2+: Glow / Pulse (Card Container)
  const glowStyle = escalationLevel >= 2
    ? { boxShadow: `0 0 15px ${baseColor.replace('1)', '0.2')}` }
    : {};

  // Level 3: "Interruptive" visual weight (Darker, more contrast)
  const bgStyle = escalationLevel === 3
    ? 'rgba(40, 0, 0, 0.98)' // Critical/Severe backdrop
    : 'rgba(20, 20, 20, 0.95)';

  // Task 6 & 7: De-Carded Design
  // "System Speech" logic: Text floats, hierarchy is defined by weight/opacity.
  
  return (
    <motion.article
      role="article"
      aria-label={`${severity} insight: ${insight.title}`}
      layout
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ 
        duration: parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--duration-medium') || '400ms') / 1000,
        ease: [0.16, 1, 0.3, 1]
      }}
      style={{
        marginBottom: 'var(--space-3)',
        padding: `var(--space-3)`,
        position: 'relative',
        background: 'var(--color-overlay)',
        backdropFilter: 'blur(20px) saturate(180%)',
        border: severity === 'critical' ? `2px solid var(--color-danger)` : `1px solid var(--color-border)`,
        borderRadius: '8px',
        transition: `border-color var(--duration-small) var(--ease-standard)`,
      }}
      whileHover={{
        borderColor: 'var(--color-border-hover)'
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
        
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          {alert ? <AlertSignal alert={alert} /> : 
            <div 
              role="img"
              aria-label={`${severity} indicator`}
              style={{ 
                width: '8px',
                height: '8px',
                borderRadius: '50%', 
                background: baseColor, 
                boxShadow: `0 0 8px ${baseColor}` 
              }} 
            />
          }
          
          <h3 style={{ 
            margin: 0, 
            fontSize: 'var(--font-size-base)', 
            fontWeight: 500,
            letterSpacing: 'var(--letter-spacing-tight)',
            color: 'var(--color-text-primary)',
            flex: 1
          }}>
            {insight.title}
          </h3>
        </div>

        {/* Content */}
        <p style={{ 
          margin: 0,
          paddingLeft: 'var(--space-3)',
          fontSize: 'var(--font-size-sm)', 
          lineHeight: 'var(--line-height-relaxed)', 
          color: 'var(--color-text-secondary)',
          fontWeight: 300
        }}>
          {insight.explanation}
          {alert && alert.message !== insight.explanation && (
            <span style={{ 
              display: 'block',
              marginTop: 'var(--space-2)',
              color: 'var(--color-text-primary)',
              fontWeight: 400
            }}>
              {alert.message}
            </span>
          )}
        </p>

        {/* Recommendation */}
        <div style={{ 
          marginLeft: 'var(--space-3)', 
          fontSize: 'var(--font-size-sm)', 
          color: baseColor,
          display: 'flex', 
          alignItems: 'center', 
          gap: 'var(--space-2)',
          opacity: 0.9
        }}>
          <span aria-hidden="true">↳</span>
          <span>{alert?.recommendedAction || insight.recommendation}</span>
        </div>
      </div>
      
      {/* Acknowledged Indicator */}
      {alert && (alert as any).state === 'acknowledged' && (
        <div style={{ 
          marginTop: 'var(--space-3)',
          fontSize: 'var(--font-size-xs)', 
          padding: 'var(--space-1) var(--space-2)',
          border: '1px solid var(--color-border)',
          borderRadius: '4px',
          display: 'inline-flex',
          alignItems: 'center',
          gap: 'var(--space-1)',
          opacity: 0.8
        }}>
          <span aria-label="acknowledged">✓</span>
          <span>Acknowledged</span>
        </div>
      )}

      {/* Footer Actions & Transparency */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginTop: 'var(--space-3)',
        paddingTop: 'var(--space-2)',
        borderTop: '1px solid var(--color-border)'
      }}>
        
        {/* Transparency */}
        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)', fontStyle: 'italic' }}>
          {transparencyExplanation && (
            <span><span aria-hidden="true">ℹ️</span> {transparencyExplanation}</span>
          )}
        </div>

        {/* Feedback Actions */}
        {!alert && (
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <button 
              onClick={handleHelpful}
              aria-label="Mark as helpful"
              style={{ 
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                fontSize: 'var(--font-size-sm)',
                opacity: 0.6,
                padding: 'var(--space-1)',
                color: 'var(--color-text-primary)',
                transition: `opacity var(--duration-micro) var(--ease-standard)`
              }}
              onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
              onMouseLeave={(e) => e.currentTarget.style.opacity = '0.6'}
            >
              👍
            </button>
            <button 
              onClick={handleDismiss}
              aria-label="Dismiss insight"
              style={{ 
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                fontSize: 'var(--font-size-sm)',
                opacity: 0.6,
                padding: 'var(--space-1)',
                color: 'var(--color-text-primary)',
                transition: `opacity var(--duration-micro) var(--ease-standard)`
              }}
              onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
              onMouseLeave={(e) => e.currentTarget.style.opacity = '0.6'}
            >
              ✕
            </button>
          </div>
        )}
      </div>

      {/* Policy Context */}
      {relevantPolicies.length > 0 && (
        <div style={{
          marginTop: 'var(--space-3)',
          paddingTop: 'var(--space-2)',
          borderTop: '1px solid rgba(255,255,255,0.05)'
        }}>
          {relevantPolicies.map(signal => (
            <PolicySignalCard key={signal.id} signal={signal} />
          ))}
        </div>
      )}

    </motion.article>
  );
}
