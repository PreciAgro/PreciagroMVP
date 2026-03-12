export type StepAcknowledgement = 'seen' | 'done' | 'skipped';

export interface GuidedStep {
  stepId: string;
  title: string;
  purpose: string;
  suggestedAction: string;
  whyItMatters: string;
  optionalEvidence?: {
    type: 'image' | 'checklist' | 'observation';
    description: string;
  };
  acknowledgementType?: StepAcknowledgement;
}

export interface EmergencyWorkflow {
  workflowId: string;
  emergencyId: string; // Links back to the triggering EmergencyAlert
  objectId: string;    // The farm object this applies to
  
  title: string;       // E.g. "Pest Outbreak Response"
  
  steps: GuidedStep[];
  currentStepIndex: number;
  
  state: 'active' | 'completed' | 'aborted';
  
  confidence: number;      // 0.0 to 1.0 (from Prompt: Uncertainty reduces depth)
  exitConditions: string[]; // List of conditions that end this workflow
}
