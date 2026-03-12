'use client';

import { useWorkflowStore } from '../../../state/useWorkflowStore';
import { WorkflowStepCard } from './WorkflowStepCard';
import { AnimatePresence, motion } from 'framer-motion';

export function GuidedActionOverlay() {
  const { activeWorkflow, nextStep, skipStep, exitWorkflow } = useWorkflowStore();

  if (!activeWorkflow || activeWorkflow.state !== 'active') return null;

  const currentStep = activeWorkflow.steps[activeWorkflow.currentStepIndex];

  return (
    <AnimatePresence mode='wait'>
      <motion.div
        key="guided-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          // Semi-transparent but DARK to focus attention
          backgroundColor: 'rgba(0, 0, 0, 0.6)', 
          zIndex: 8000, // Below EmergencyOverlay (9999) but above everything else
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          pointerEvents: 'auto' // Blocks interaction with farm while guiding
        }}
      >
        {/* Exit Button (Top Right) */}
        <button
            onClick={exitWorkflow}
            style={{
                position: 'absolute',
                top: '2rem',
                right: '2rem',
                background: 'transparent',
                border: 'none',
                color: 'rgba(255,255,255,0.6)',
                fontSize: '1rem',
                cursor: 'pointer'
            }}
        >
            Exit Guidance ✕
        </button>

        {/* The Card */}
        <WorkflowStepCard 
            step={currentStep}
            stepIndex={activeWorkflow.currentStepIndex}
            totalSteps={activeWorkflow.steps.length}
            onComplete={nextStep}
            onSkip={skipStep}
        />
      </motion.div>
    </AnimatePresence>
  );
}
