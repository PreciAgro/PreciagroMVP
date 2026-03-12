import React from 'react';
import { Season } from '../../../core/models/StrategicContext';

interface StrategicTimelineProps {
    history: Season[];
    current: Season;
    projections: Season[];
}

export const StrategicTimeline: React.FC<StrategicTimelineProps> = ({ history, current, projections }) => {
    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem',
            padding: '2rem 0',
            width: '100%'
        }}>
            {/* Historical Seasons - Solid, Muted */}
            {history.map(s => (
                <div key={s.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: 0.6 }}>
                    <div style={{
                        width: '100px',
                        height: '4px',
                        background: '#666',
                        borderRadius: '2px'
                    }} />
                    <span style={{ fontSize: '0.75rem', marginTop: '0.5rem', color: '#888' }}>{s.label}</span>
                </div>
            ))}

            {/* Current Season - Active, Highlighted */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div style={{
                    width: '120px',
                    height: '6px',
                    background: '#fff',
                    borderRadius: '3px',
                    boxShadow: '0 0 10px rgba(255,255,255,0.3)'
                }} />
                <span style={{ fontSize: '0.85rem', marginTop: '0.5rem', color: '#fff', fontWeight: 'bold' }}>{current.label}</span>
            </div>

            {/* Projected Seasons - Dashed, Soft */}
            {projections.map(s => (
                <div key={s.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: 0.5 }}>
                    <div style={{
                        width: '100px',
                        height: '4px',
                        borderBottom: '2px dashed #666',
                        borderRadius: '2px'
                    }} />
                    <span style={{ fontSize: '0.75rem', marginTop: '0.5rem', color: '#888' }}>{s.label}</span>
                </div>
            ))}
        </div>
    );
};
