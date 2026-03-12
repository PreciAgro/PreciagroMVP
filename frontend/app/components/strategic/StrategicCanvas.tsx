import React from 'react';
import { useStrategicStore } from '../../../state/useStrategicStore';
import { StrategicTimeline } from './StrategicTimeline';
import { TradeOffCard } from './TradeOffCard';
import { StrategicPath, StrategicOutcome } from '../../../core/models/StrategicContext';

export const StrategicCanvas: React.FC = () => {
    const { context, activeStrategyId, comparedStrategyId, setScenario, setComparison } = useStrategicStore();

    const activeStrategy = context.availableStrategies.find(s => s.id === activeStrategyId);
    
    // Helper to render strategy details
    const renderStrategyColumn = (strategy: StrategicPath, isPrimary: boolean) => (
        <div style={{
            flex: 1,
            background: isPrimary ? 'rgba(20,20,20,0.8)' : 'rgba(30,30,30,0.5)',
            border: isPrimary ? '1px solid #444' : '1px dashed #444',
            borderRadius: '12px',
            padding: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
            transition: 'all 0.3s ease'
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#fff' }}>{strategy.name}</h3>
                {isPrimary && <span style={{ fontSize: '0.7rem', background: '#333', padding: '2px 6px', borderRadius: '4px', color: '#aaa' }}>CURRENT PATH</span>}
            </div>
            
            <p style={{ fontSize: '0.9rem', color: '#aaa', lineHeight: 1.5, margin: 0 }}>
                {strategy.description}
            </p>

            {/* Phase 10: Policy Alignment & Constraints */}
            {(strategy.policyAlignment || (strategy.systemConstraints && strategy.systemConstraints.length > 0)) && (
                <div style={{ background: 'rgba(30, 40, 50, 0.5)', padding: '0.8rem', borderRadius: '6px', borderLeft: '3px solid #60a5fa' }}>
                    {strategy.policyAlignment && (
                         <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#60a5fa', fontWeight: 600, marginBottom: '0.4rem' }}>
                             Policy Status: {strategy.policyAlignment.replace('_', ' ')}
                         </div>
                    )}
                    {strategy.systemConstraints && strategy.systemConstraints.map((constraint, idx) => (
                        <div key={idx} style={{ fontSize: '0.8rem', color: '#ccc', display: 'flex', gap: '0.5rem' }}>
                            <span>•</span>
                            <span>{constraint}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* Outcomes Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '0.75rem' }}>
                {strategy.outcomes.map((outcome, idx) => (
                    <div key={idx} style={{ background: '#111', padding: '0.75rem', borderRadius: '6px' }}>
                        <span style={{ fontSize: '0.7rem', color: '#666', display: 'block' }}>{outcome.label}</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.25rem' }}>
                            <span style={{ color: '#ddd', fontSize: '0.9rem' }}>{outcome.value}</span>
                            {outcome.trend === 'improving' && <span style={{ color: '#4ade80', fontSize: '10px' }}>▲</span>}
                            {outcome.trend === 'declining' && <span style={{ color: '#f87171', fontSize: '10px' }}>▼</span>}
                        </div>
                    </div>
                ))}
            </div>

            {/* Trade Offs */}
            <div>
                {strategy.tradeOffs.map((to, idx) => (
                    <TradeOffCard key={idx} tradeOff={to} />
                ))}
            </div>
        </div>
    );

    return (
        <div style={{
            position: 'absolute',
            top: 0, left: 0, width: '100%', height: '100%',
            backgroundColor: '#050505',
            color: '#e0e0e0',
            zIndex: 50, // Above map layer
            display: 'flex',
            flexDirection: 'column',
            padding: '2rem'
        }}>
            {/* Header / Timeline Area */}
            <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: 300, letterSpacing: '1px', color: '#888' }}>
                    STRATEGIC FORESIGHT
                </h2>
                <StrategicTimeline 
                    history={context.history} 
                    current={MOCK_CURRENT} 
                    projections={context.projections} 
                /> 
            </div>

            {/* Comparison Area */}
            <div style={{ display: 'flex', gap: '2rem', flex: 1, overflowY: 'auto', paddingBottom: '2rem' }}>
                
                {/* Primary Strategy (Active) */}
                {activeStrategy && renderStrategyColumn(activeStrategy, true)}

                {/* Secondary Slot / Selector */}
                {comparedStrategyId ? (
                    // Show Compared Strategy
                    context.availableStrategies.find(s => s.id === comparedStrategyId) && 
                    renderStrategyColumn(context.availableStrategies.find(s => s.id === comparedStrategyId)!, false)
                ) : (
                    // Empty Slot - Select Alternative
                    <div style={{
                        flex: 1,
                        border: '1px dashed #333',
                        borderRadius: '12px',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#444'
                    }}>
                        <span style={{ marginBottom: '1rem' }}>Compare Alternative Path</span>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                            {context.availableStrategies.filter(s => s.id !== activeStrategyId).map(s => (
                                <button
                                    key={s.id}
                                    onClick={() => setComparison(s.id)}
                                    style={{
                                        background: '#222',
                                        border: '1px solid #444',
                                        color: '#aaa',
                                        padding: '0.5rem 1rem',
                                        borderRadius: '6px',
                                        cursor: 'pointer'
                                    }}
                                >
                                    + {s.name}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Exit Instruction */}
            <div style={{ textAlign: 'center', color: '#444', fontSize: '0.8rem', marginTop: '1rem' }}>
                Selecting a strategy does not auto-apply it. Verification required before commitment.
            </div>
        </div>
    );
};

// Quick fix for the MOCK_CURRENT reference issue
const MOCK_CURRENT = { 
    id: '2025-planting', year: 2025, type: 'current', label: '2025 Planting', status: 'active' 
} as any; 
