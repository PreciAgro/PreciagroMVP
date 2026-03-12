'use client';

import { GuidedStep } from "../../../core/models/GuidedWorkflow";
import { motion } from "framer-motion";

interface Props {
    step: GuidedStep;
    stepIndex: number;
    totalSteps: number;
    onComplete: () => void;
    onSkip: () => void;
}

export function WorkflowStepCard({ step, stepIndex, totalSteps, onComplete, onSkip }: Props) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            style={{
                background: 'rgba(20, 20, 20, 0.9)',
                backdropFilter: 'blur(12px)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: '16px',
                padding: '2rem',
                maxWidth: '500px',
                width: '100%',
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
                display: 'flex',
                flexDirection: 'column',
                gap: '1.5rem',
                color: '#e5e5e5'
            }}
        >
            {/* Header: Progress & Title */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', opacity: 0.6, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                <span>Step {stepIndex + 1} of {totalSteps}</span>
                <span>Guided Response</span>
            </div>

            {/* Main Content */}
            <div>
                <h2 style={{ fontSize: '1.75rem', fontWeight: 600, color: '#fff', marginBottom: '0.5rem' }}>
                    {step.title}
                </h2>
                <p style={{ fontSize: '1rem', lineHeight: '1.5', opacity: 0.9 }}>
                    {step.purpose}
                </p>
            </div>

            {/* Action Box */}
            <div style={{
                background: 'rgba(255, 255, 255, 0.05)',
                borderLeft: '4px solid #3b82f6', // Calm Blue for guidance
                padding: '1rem',
                borderRadius: '0 8px 8px 0'
            }}>
                <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: '#93c5fd', marginBottom: '0.25rem', fontWeight: 700 }}>
                    Recommended Action
                </div>
                <div style={{ fontSize: '1.1rem', fontWeight: 500 }}>
                    {step.suggestedAction}
                </div>
            </div>

            <p style={{ fontSize: '0.9rem', fontStyle: 'italic', opacity: 0.7 }}>
                Why: {step.whyItMatters}
            </p>

            {/* Controls */}
            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                <button
                    onClick={onComplete}
                    style={{
                        flex: 2,
                        background: '#3b82f6', // Blue-500
                        color: '#fff',
                        border: 'none',
                        padding: '0.875rem',
                        borderRadius: '8px',
                        fontSize: '1rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        transition: 'background 0.2s'
                    }}
                    onMouseOver={(e) => e.currentTarget.style.background = '#2563eb'}
                    onMouseOut={(e) => e.currentTarget.style.background = '#3b82f6'}
                >
                    Mark Complete
                </button>
                
                <button
                    onClick={onSkip}
                    style={{
                        flex: 1,
                        background: 'transparent',
                        color: '#9ca3af',
                        border: '1px solid rgba(255,255,255,0.2)',
                        padding: '0.875rem',
                        borderRadius: '8px',
                        fontSize: '1rem',
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                    }}
                    onMouseOver={(e) => {
                        e.currentTarget.style.borderColor = '#fff';
                        e.currentTarget.style.color = '#fff';
                    }}
                    onMouseOut={(e) => {
                        e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)';
                        e.currentTarget.style.color = '#9ca3af';
                    }}
                >
                    Skip
                </button>
            </div>
        </motion.div>
    );
}
