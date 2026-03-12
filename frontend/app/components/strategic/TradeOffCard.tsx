import React from 'react';
import { StrategicTradeOff, StrategicConfidence } from '../../../core/models/StrategicContext';

interface TradeOffCardProps {
    tradeOff: StrategicTradeOff;
}

const CONFIDENCE_COLORS: Record<StrategicConfidence, string> = {
    'low': '#d97706', // amber
    'medium': '#eab308', // yellow
    'high': '#22c55e' // green
};

export const TradeOffCard: React.FC<TradeOffCardProps> = ({ tradeOff }) => {
    return (
        <div style={{
            background: 'rgba(255,255,255,0.05)',
            border: '1px solid #333',
            borderRadius: '8px',
            padding: '1rem',
            marginTop: '1rem'
        }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                {/* Upside */}
                <div>
                    <span style={{ fontSize: '0.7rem', color: '#4ade80', textTransform: 'uppercase', display: 'block', marginBottom: '0.25rem' }}>
                        Potential Upside
                    </span>
                    <p style={{ fontSize: '0.9rem', color: '#e0e0e0', margin: 0 }}>
                        {tradeOff.upside}
                    </p>
                </div>

                {/* Downside - CRITICAL for this phase */}
                <div style={{ borderLeft: '1px solid #444', paddingLeft: '1rem' }}>
                     <span style={{ fontSize: '0.7rem', color: '#f87171', textTransform: 'uppercase', display: 'block', marginBottom: '0.25rem' }}>
                        Trade-Off / Risk
                    </span>
                    <p style={{ fontSize: '0.9rem', color: '#d1d5db', margin: 0 }}>
                        {tradeOff.downside}
                    </p>
                </div>
            </div>

            {/* Uncertainty Footer */}
            <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid #333', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                 <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div style={{ 
                        width: '8px', 
                        height: '8px', 
                        borderRadius: '50%', 
                        backgroundColor: CONFIDENCE_COLORS[tradeOff.uncertainty] 
                    }} />
                    <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
                        Certainty Level: <span style={{ textTransform: 'capitalize' }}>{tradeOff.uncertainty}</span>
                    </span>
                 </div>
                 
                 {/* Phase 10: Policy Relevance */}
                 {tradeOff.policyRelevance && (
                     <div style={{ fontSize: '0.75rem', color: '#60a5fa', display: 'flex', alignItems: 'flex-start', gap: '0.4rem' }}>
                         <span>🏛️</span>
                         <span style={{ fontStyle: 'italic' }}>{tradeOff.policyRelevance}</span>
                     </div>
                 )}
            </div>
        </div>
    );
};
