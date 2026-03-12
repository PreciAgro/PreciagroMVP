import { PolicyBoundary, PolicySignal, PolicyConflict } from '../models/PolicyContext';
import { MOCK_POLICIES } from '../mocks/policyData';

/**
 * PolicyEngine - Generates neutral, contextual policy signals
 * Phase 10: System-Level & Policy-Aware Intelligence
 * 
 * CORE PRINCIPLE: The system informs. The human decides. The law constrains.
 */
export class PolicyEngine {
  
  // Forbidden phrases that indicate enforcement rather than information
  private static readonly FORBIDDEN_PHRASES = [
    'illegal', 'not allowed', 'blocked', 'must comply',
    'violation', 'prohibited', 'forbidden', 'mandatory',
    'you cannot', 'you must', 'required to'
  ];

  /**
   * Evaluate which policies are relevant given current context
   */
  static evaluatePolicyRelevance(
    farmContext: { region: string; cropType: string; season: string },
    actionType?: string
  ): PolicyBoundary[] {
    const relevantPolicies: PolicyBoundary[] = [];
    
    // Load mock policies
    const allPolicies = this.getMockPolicies();
    
    // Filter by region and crop type
    for (const policy of allPolicies) {
      const ctx = policy.applicableContext;
      
      const regionMatches = ctx.region === farmContext.region || ctx.region === 'all';
      const cropMatches = ctx.cropTypes.length === 0 || ctx.cropTypes.includes(farmContext.cropType);
      const timeMatches = this.isTimeRelevant(ctx.effectiveFrom, ctx.effectiveUntil);
      
      if (regionMatches && cropMatches && timeMatches) {
        relevantPolicies.push(policy);
      }
    }
    
    return relevantPolicies;
  }

  /**
   * Generate neutral policy signal from boundary
   * ENFORCES NEUTRAL LANGUAGE
   */
  static generatePolicySignal(boundary: PolicyBoundary): PolicySignal {
    const message = this.createNeutralMessage(boundary);
    
    // Validate tone before returning
    if (!this.validateNeutralTone(message)) {
      console.error('Policy message failed neutrality check:', message);
      throw new Error('Policy message contains enforcement language');
    }
    
    return {
      id: `signal-${boundary.id}`,
      boundaryId: boundary.id,
      message,
      boundaryType: boundary.type,
      applicability: this.getApplicabilityContext(boundary),
      reason: boundary.description,
      confidence: 0.9 // High confidence for official policy
    };
  }

  /**
   * Detect conflicts between farmer goals and policies
   * Returns conflict with trade-offs, NEVER moralizes
   */
  static checkConflict(
    farmerAction: string,
    farmerGoal: string,
    relevantPolicies: PolicyBoundary[]
  ): PolicyConflict | null {
    // Check if any policies create tension with the goal
    const conflictingPolicy = relevantPolicies.find(p => 
      this.hasConflict(farmerAction, p)
    );
    
    if (!conflictingPolicy) return null;
    
    return {
      type: 'goal_vs_policy',
      description: `This approach may support ${farmerGoal} but could conflict with ${conflictingPolicy.description}`,
      farmerGoal,
      policyConstraint: conflictingPolicy.description,
      tradeoff: {
        chooseFarmerGoal: `Proceeding may achieve ${farmerGoal} in the short term`,
        choosePolicy: `Aligning with guidelines may provide long-term benefits`
      }
    };
  }

  // --- PRIVATE HELPERS ---

  private static createNeutralMessage(boundary: PolicyBoundary): string {
    const templates = {
      advisory: `Local guidelines recommend: ${boundary.description}`,
      regulatory: `This action may be affected by: ${boundary.description}`,
      environmental: `Environmental context: ${boundary.description}`
    };
    
    return templates[boundary.type];
  }

  private static getApplicabilityContext(boundary: PolicyBoundary): string {
    const ctx = boundary.applicableContext;
    const timeframe = ctx.effectiveUntil 
      ? `from ${ctx.effectiveFrom} to ${ctx.effectiveUntil}`
      : `starting ${ctx.effectiveFrom}`;
    
    return `Applies to ${ctx.cropTypes.join(', ')} in ${ctx.region} region ${timeframe}`;
  }

  private static validateNeutralTone(message: string): boolean {
    const lower = message.toLowerCase();
    return !this.FORBIDDEN_PHRASES.some(phrase => lower.includes(phrase));
  }

  private static isTimeRelevant(effectiveFrom: string, effectiveUntil?: string): boolean {
    const now = new Date();
    const from = new Date(effectiveFrom);
    
    if (now < from) return false;
    if (effectiveUntil) {
      const until = new Date(effectiveUntil);
      if (now > until) return false;
    }
    
    return true;
  }

  private static hasConflict(action: string, policy: PolicyBoundary): boolean {
    // Simple keyword matching for demo
    // In production, this would use more sophisticated logic
    const keywords = policy.description.toLowerCase().split(' ');
    const actionLower = action.toLowerCase();
    
    return keywords.some(kw => actionLower.includes(kw));
  }

  private static getMockPolicies(): PolicyBoundary[] {
    return MOCK_POLICIES;
  }
}
