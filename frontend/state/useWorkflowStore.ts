import { create } from 'zustand';
import { EmergencyWorkflow } from '../core/models/GuidedWorkflow';
import { MOCK_WORKFLOWS } from '../core/mocks/MockWorkflows';

interface WorkflowState {
  activeWorkflow: EmergencyWorkflow | null;
  
  // Actions
  startWorkflow: (emergencyId: string) => void;
  nextStep: () => void;
  skipStep: () => void; // Skipping is valid and non-punitive
  exitWorkflow: () => void;
  
  // Helpers
  getWorkflowProgress: () => number; // 0.0 to 1.0
}

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  activeWorkflow: null,

  startWorkflow: (emergencyId: string) => {
    console.log(`[WorkflowEngine] Looking for workflow for emergency: ${emergencyId}`);
    
    // In a real app, we'd fetch from backend.
    // Here, we look up our mock data.
    // For demo purposes, we'll map *any* critical alert to our pest workflow if it matches, 
    // or just default to the pest one for testing if the ID matches our mock pattern.
    
    let workflow = Object.values(MOCK_WORKFLOWS).find(w => w.emergencyId === emergencyId);
    
    // FALLBACK FOR DEMO: If the ID contains 'pest', load the pest workflow
    if (!workflow && emergencyId.includes('pest')) {
        workflow = MOCK_WORKFLOWS['pest-outbreak-001'];
    }

    if (workflow) {
      console.log(`[WorkflowEngine] Starting workflow: ${workflow.title}`);
      set({ 
        activeWorkflow: { 
            ...workflow, 
            currentStepIndex: 0, 
            state: 'active' 
        } 
      });
    } else {
      console.warn(`[WorkflowEngine] No workflow found for emergency: ${emergencyId}`);
    }
  },

  nextStep: () => {
    const { activeWorkflow } = get();
    if (!activeWorkflow) return;

    const nextIndex = activeWorkflow.currentStepIndex + 1;
    
    if (nextIndex < activeWorkflow.steps.length) {
      set({ 
        activeWorkflow: { 
          ...activeWorkflow, 
          currentStepIndex: nextIndex 
        } 
      });
    } else {
      // End of workflow
      console.log("[WorkflowEngine] Workflow completed.");
      set({ 
          activeWorkflow: { ...activeWorkflow, state: 'completed' } 
      });
      // Optional: Auto-exit or wait for user to dismiss "All Done" screen?
      // Per prompt: "workflow fades calmly", "no completion celebration".
      // We will likely mark it completed and let the UI handle the "Exit" transition.
      setTimeout(() => get().exitWorkflow(), 1500); // Auto-fade after short delay or let UI handle it?
      // Better: Let UI show "Complete" state, user manually exits or it auto-closes.
      // For now, let's just mark completed.
    }
  },

  skipStep: () => {
      // Skipping is functionally same as next step, but might log 'skipped' status for the step
      get().nextStep();
  },

  exitWorkflow: () => {
    set({ activeWorkflow: null });
  },

  getWorkflowProgress: () => {
      const { activeWorkflow } = get();
      if (!activeWorkflow) return 0;
      return (activeWorkflow.currentStepIndex + 1) / activeWorkflow.steps.length;
  }
}));
