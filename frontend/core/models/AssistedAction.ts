// Phase 7: Assisted Execution Types

export type AssistanceCategory = 'preparation' | 'coordination' | 'simulation';

export type AssistanceState = 
  | 'idle' 
  | 'preparing' 
  | 'ready_for_review' 
  | 'authorizing' 
  | 'executing' 
  | 'completed'
  | 'cancelled';

export interface PreparationStep {
  id: string;
  label: string;
  status: 'pending' | 'processing' | 'done';
}

export interface RiskAssessment {
  level: 'low' | 'medium' | 'high';
  implication: string;
  mitigation: string;
}

export interface AssistedAction {
  id: string;
  title: string;
  category: AssistanceCategory;
  description: string;
  
  // Explicit Authorization Content
  willDo: string[];
  willNotDo: string[];
  userResponsibility: string[];

  // Execution Details
  preparationSteps: PreparationStep[];
  estimatedDurationSeconds: number;
  
  // Safety
  risk: RiskAssessment;
  reversible: boolean;
  reversalLabel?: string; // e.g. "Undo Draft", "Cancel Schedule"
}

export interface ExecutionLogEntry {
  actionId: string;
  timestamp: string; // ISO
  userHash: string; // Mock user ID
  authorized: boolean;
  outcome: 'success' | 'failure';
}
