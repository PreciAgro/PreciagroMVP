// System-Level Awareness Models
// Phase 10: System-Level & Policy-Aware Intelligence

export interface ResourceConstraint {
  type: 'water' | 'soil_nitrogen' | 'pest_pressure';
  currentLevel: number; // 0-100 scale
  threshold: number;
  trend: 'improving' | 'stable' | 'declining';
  timeframe: string; // "this season"
}

export interface EnvironmentalLoad {
  indicator: string; // "Regional water stress"
  regionalLevel: 'low' | 'moderate' | 'high';
  farmerContribution?: never; // MUST NEVER track individual contribution
  trend: 'improving' | 'stable' | 'worsening';
}

export interface AggregateSignal {
  metric: string; // "Water usage trends"
  trend: string; // "Regional water stress is increasing"
  anonymizedContext: string; // "Multiple farms report similar conditions"
  relevance: string; // "Practices that reduce usage may become more important"
}
