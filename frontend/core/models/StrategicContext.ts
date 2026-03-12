export type StrategicConfidence = 'low' | 'medium' | 'high';
export type StrategicRiskLevel = 'minimal' | 'moderate' | 'significant';

export interface StrategicTradeOff {
    upside: string;
    downside: string;
    uncertainty: StrategicConfidence;
    policyRelevance?: string; // Optional policy context (Phase 10)
}

export interface StrategicOutcome {
    label: string;
    value: string; // e.g. "Yield +5%" or "Soil Health: Excellent"
    trend: 'improving' | 'stable' | 'declining';
}

export interface StrategicPath {
    id: string;
    name: string;
    description: string;
    timeframeYears: number;
    outcomes: StrategicOutcome[];
    tradeOffs: StrategicTradeOff[];
    risks: string[]; // List of specific risks e.g., "Pest recurrence"
    overallConfidence: StrategicConfidence;
    systemConstraints?: string[]; // Policy/environmental constraints (Phase 10)
    policyAlignment?: 'aligned' | 'partial' | 'potential_conflict'; // Phase 10
}

export interface Season {
    id: string; // e.g., "2024-Harvest"
    year: number;
    type: 'historical' | 'current' | 'projected';
    label: string;
    status: 'completed' | 'active' | 'future';
}

export interface MultiSeasonContext {
    currentSeasonId: string;
    history: Season[];
    projections: Season[]; // Future windows
    availableStrategies: StrategicPath[];
}
