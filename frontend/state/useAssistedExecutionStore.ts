import { create } from 'zustand';
import { AssistedAction, AssistanceState, ExecutionLogEntry } from '../core/models/AssistedAction';

interface AssistedExecutionState {
  // Current Active Assistance
  currentAction: AssistedAction | null;
  status: AssistanceState;
  
  // Progress tracking
  progress: number; // 0-100
  
  // Audit Log (In-Memory for MVP)
  auditLog: ExecutionLogEntry[];

  // Actions
  selectAction: (action: AssistedAction) => void;
  startPreparation: () => Promise<void>;
  cancelPreparation: () => void;
  confirmAuthorization: () => void;
  executeAction: () => Promise<void>;
  reset: () => void;
  undoLastAction: () => void;
}

export const useAssistedExecutionStore = create<AssistedExecutionState>((set, get) => ({
  currentAction: null,
  status: 'idle',
  progress: 0,
  auditLog: [],

  selectAction: (action) => {
    if (get().status !== 'idle') return;
    set({ currentAction: action, status: 'idle', progress: 0 });
  },

  startPreparation: async () => {
    const { currentAction, status } = get();
    if (!currentAction || status !== 'idle') return;

    set({ status: 'preparing', progress: 10 });

    // Mock preparation delay (Slow on Purpose)
    await new Promise(resolve => setTimeout(resolve, 1500));
    set({ progress: 50 });
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    set({ status: 'ready_for_review', progress: 100 });
  },

  cancelPreparation: () => {
    set({ status: 'idle', progress: 0 });
  },

  confirmAuthorization: () => {
    const { status } = get();
    if (status === 'ready_for_review') {
      set({ status: 'authorizing' });
    }
  },

  executeAction: async () => {
    const { currentAction, status } = get();
    if (!currentAction || status !== 'authorizing') return;

    set({ status: 'executing' });

    // Mock execution delay
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Log the execution
    const logEntry: ExecutionLogEntry = {
      actionId: currentAction.id,
      timestamp: new Date().toISOString(),
      userHash: 'farmer_001', // Mock
      authorized: true,
      outcome: 'success'
    };

    set(state => ({
      status: 'completed',
      auditLog: [logEntry, ...state.auditLog]
    }));
  },

  undoLastAction: () => {
    // Only simple state reset for MVP, in real app this would trigger specific undo logic
    const { currentAction, status } = get();
    if (status !== 'completed' || !currentAction?.reversible) return;
    
    console.log(`[Undo] Reversing action: ${currentAction.id}`);
    set({ status: 'idle', progress: 0, currentAction: null });
  },

  reset: () => {
    set({ status: 'idle', currentAction: null, progress: 0 });
  }
}));
