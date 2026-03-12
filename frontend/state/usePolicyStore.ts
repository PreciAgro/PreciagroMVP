import { create } from 'zustand';
import { PolicyJurisdiction, PolicySignal, PolicyConflict } from '../core/models/PolicyContext';
import { AggregateSignal, ResourceConstraint } from '../core/models/SystemContext';
import { PolicyEngine } from '../core/intelligence/PolicyEngine';
import { SystemAwarenessEngine } from '../core/intelligence/SystemAwarenessEngine';

interface PolicyState {
  currentJurisdiction: PolicyJurisdiction | null;
  activePolicySignals: PolicySignal[];
  systemAwarenessSignals: AggregateSignal[];
  resourceConstraints: ResourceConstraint[];
  acknowledgedPolicies: Set<string>;

  // Actions
  updatePolicyContext: (context: { region: string; cropType: string; season: string }) => void;
  acknowledgePolicy: (policyId: string) => void;
  getPolicyForAction: (actionType: string) => PolicySignal[];
  getActiveConflicts: (actionType: string, goal: string) => PolicyConflict | null;
}

export const usePolicyStore = create<PolicyState>((set, get) => ({
  currentJurisdiction: null,
  activePolicySignals: [],
  systemAwarenessSignals: [],
  resourceConstraints: [],
  acknowledgedPolicies: new Set(),

  updatePolicyContext: (context) => {
    // 1. Evaluate relevant policies
    const policies = PolicyEngine.evaluatePolicyRelevance({
      region: context.region,
      cropType: context.cropType,
      season: context.season
    });

    // 2. Generate signals
    const signals = policies.map(p => PolicyEngine.generatePolicySignal(p));

    // 3. Get System Awareness
    const systemSignals = SystemAwarenessEngine.generateAggregateSignals(context.region, context.season);
    const resources = SystemAwarenessEngine.assessResourceConstraints(context);

    // 4. Update Jurisdiction (simplified for now)
    const jurisdiction: PolicyJurisdiction = {
        region: context.region,
        cropTypes: [context.cropType],
        effectiveFrom: new Date().toISOString()
    };

    set({
      currentJurisdiction: jurisdiction,
      activePolicySignals: signals,
      systemAwarenessSignals: systemSignals,
      resourceConstraints: resources
    });
  },

  acknowledgePolicy: (policyId) => {
    set((state) => {
      const newSet = new Set(state.acknowledgedPolicies);
      newSet.add(policyId);
      return { acknowledgedPolicies: newSet };
    });
  },

  getPolicyForAction: (actionType) => {
    const { activePolicySignals } = get();
    // In a real engine, we'd map actionType to applicable policies more smartly
    // For now, return all active signals that might apply
    return activePolicySignals; 
  },

  getActiveConflicts: (actionType, goal) => {
      // Re-evaluate policies against the specific action
      const { currentJurisdiction } = get();
      if (!currentJurisdiction) return null;

      // We need to fetch the raw boundaries again to check for conflicts
      // (Store usually keeps signals, but Engine needs boundaries for conflict check)
      // This is a slight simplification used for the MVP
      const policies = PolicyEngine.evaluatePolicyRelevance({
          region: currentJurisdiction.region,
          cropType: currentJurisdiction.cropTypes[0] || 'unknown',
          season: 'active' // simplified
      });

      return PolicyEngine.checkConflict(actionType, goal, policies);
  }
}));
