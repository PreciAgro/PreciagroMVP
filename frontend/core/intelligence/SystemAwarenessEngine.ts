import { ResourceConstraint, EnvironmentalLoad, AggregateSignal } from '../models/SystemContext';

/**
 * SystemAwarenessEngine - Generates anonymized system-level intelligence
 * Phase 10: System-Level & Policy-Aware Intelligence
 * 
 * CRITICAL: All signals must be anonymized. NO individual farmer tracking.
 */
export class SystemAwarenessEngine {
  
  /**
   * Generate regional environmental signals
   * Returns anonymized regional trends
   * NO individual farmer data
   */
  static generateAggregateSignals(region: string, season: string): AggregateSignal[] {
    // TODO: In production, this would aggregate actual regional data
    // For now, returns mock aggregated signals
    
    const signals: AggregateSignal[] = [];
    
    // Example: Water stress signal
    if (this.shouldSignalWaterStress(region, season)) {
      signals.push({
        metric: 'Regional Water Availability',
        trend: 'Regional water stress is increasing this season',
        anonymizedContext: 'Multiple farms in the region are experiencing similar conditions',
        relevance: 'Practices that reduce water usage may become more important'
      });
    }
    
    // Example: Pest pressure signal
    if (this.shouldSignalPestPressure(region, season)) {
      signals.push({
        metric: 'Regional Pest Activity',
        trend: 'Elevated pest pressure detected across the region',
        anonymizedContext: 'Regional monitoring indicates increased activity',
        relevance: 'Early detection practices may help manage risk'
      });
    }
    
    return signals;
  }

  /**
   * Evaluate environmental load
   * Returns environmental indicators
   * MUST be anonymized
   */
  static evaluateEnvironmentalLoad(region: string): EnvironmentalLoad[] {
    const loads: EnvironmentalLoad[] = [];
    
    // Mock implementation
    // In production, this would query environmental monitoring systems
    
    loads.push({
      indicator: 'Regional water stress index',
      regionalLevel: 'moderate',
      trend: 'worsening'
    });
    
    return loads;
  }

  /**
   * Assess resource constraints
   * Returns resource status (water, soil, etc.)
   */
  static assessResourceConstraints(
    farmContext: { region: string; cropType: string; season: string }
  ): ResourceConstraint[] {
    const constraints: ResourceConstraint[] = [];
    
    // Mock implementation
    // In production, this would use actual sensor/monitoring data
    
    // Example: Water availability constraint
    if (farmContext.season === 'dry') {
      constraints.push({
        type: 'water',
        currentLevel: 45, // 0-100 scale
        threshold: 60,
        trend: 'declining',
        timeframe: 'this season'
      });
    }
    
    return constraints;
  }

  // --- PRIVATE HELPERS ---

  private static shouldSignalWaterStress(region: string, season: string): boolean {
    // Mock logic - in production, this would check actual data
    return season === 'dry' || season === 'summer';
  }

  private static shouldSignalPestPressure(region: string, season: string): boolean {
    // Mock logic - in production, this would check actual monitoring data
    return season === 'planting' || season === 'spring';
  }
}
