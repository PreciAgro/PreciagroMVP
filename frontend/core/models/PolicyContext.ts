// Policy-Aware Intelligence Models
// Phase 10: System-Level & Policy-Aware Intelligence

export interface PolicyJurisdiction {
  region: string;
  cropTypes: string[];
  effectiveFrom: string;
  effectiveUntil?: string;
}

export interface PolicyBoundary {
  id: string;
  type: 'advisory' | 'regulatory' | 'environmental';
  description: string;
  severityLevel: 'info' | 'caution' | 'critical';
  source: string;
  applicableContext: PolicyJurisdiction;
}

export interface PolicySignal {
  id: string;
  boundaryId: string;
  message: string;
  boundaryType: 'advisory' | 'regulatory' | 'environmental';
  applicability: string; // "Applies during planting season in your region"
  reason: string; // "Local water conservation guidelines"
  confidence: number;
}

export interface PolicyConflict {
  type: 'goal_vs_policy' | 'policy_vs_policy';
  description: string;
  farmerGoal?: string;
  policyConstraint: string;
  tradeoff: {
    chooseFarmerGoal: string;
    choosePolicy: string;
  };
}
