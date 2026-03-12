import { EmergencyWorkflow } from '../models/GuidedWorkflow';

export const MOCK_WORKFLOWS: Record<string, EmergencyWorkflow> = {
  'pest-outbreak-001': {
    workflowId: 'wf-pest-001',
    emergencyId: 'alert-mock-critical-pest', // Maps to a potential alert ID
    objectId: 'field-sector-north',
    title: 'Locust Swarm Response',
    confidence: 0.9,
    state: 'active',
    currentStepIndex: 0,
    exitConditions: [
        "Swarm clears",
        "Treatment completed",
        "Risk de-escalated by user command"
    ],
    steps: [
      {
        stepId: 'step-1',
        title: 'Assess Density',
        purpose: 'Determine the scale of the infestation before acting.',
        suggestedAction: 'Walk a 10m line and count visible locusts.',
        whyItMatters: 'Over-treating minor swarms wastes resources; under-treating major ones risks crop failure.',
        acknowledgementType: 'seen'
      },
      {
        stepId: 'step-2',
        title: 'Select Control Agent',
        purpose: 'Choose the correct bio-pesticide based on current stage.',
        suggestedAction: 'For count > 50/m², select Agent Green-Label.',
        whyItMatters: 'Wrong agents can harm local pollinators.',
        acknowledgementType: 'seen'
      },
      {
        stepId: 'step-3',
        title: 'Apply Treatment',
        purpose: 'Execute targeted spraying in North Sector.',
        suggestedAction: 'Deploy drone or manual spray for Sector N1.',
        whyItMatters: 'Targeted application reduces chemical runoff.',
        acknowledgementType: 'seen'
      }
    ]
  }
};
