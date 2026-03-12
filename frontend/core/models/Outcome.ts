export type OutcomeSignal = 'dismiss' | 'complete' | 'correct' | 'ignore' | 'positive_feedback' | 'negative_feedback';

export interface OutcomeContext {
  featureId: string;      // e.g., 'insight-card', 'emergency-overlay'
  contentKey: string;     // e.g., 'pest_alert_fall_armyworm', 'inspection_reminder'
  timestamp: string;      // ISO date
}

export interface OutcomeEvent {
  id: string;
  signal: OutcomeSignal;
  context: OutcomeContext;
  correctionValue?: string; // If signal is 'correct', what was the user's input?
}

export interface CalibrationFactor {
  contentKey: string;
  factor: number;         // Multiplier, e.g., 1.0 = neutral, 0.8 = lower confidence
  lastUpdated: string;
  sampleSize: number;
}
