import { CalibrationFactor, OutcomeEvent } from '../models/Outcome';

export class LearningEngine {
  private static readonly DECAY_RATE = 0.95; // Old events matter less
  private static readonly BASE_FACTOR = 1.0;
  private static readonly MIN_FACTOR = 0.5;  // Don't suppress below 50%
  private static readonly MAX_FACTOR = 1.5;  // Don't boost above 150%

  /**
   * Calculates a confidence calibration factor based on a history of outcomes.
   */
  public static calculateCalibration(history: OutcomeEvent[]): number {
    if (!history || history.length === 0) return this.BASE_FACTOR;

    // Sort by recent first
    const sortedHistory = [...history].sort((a, b) => 
      new Date(b.context.timestamp).getTime() - new Date(a.context.timestamp).getTime()
    );

    let currentScore = 0;
    let totalWeight = 0;

    // We take the last 10 relevant events
    const recentEvents = sortedHistory.slice(0, 10);

    recentEvents.forEach((event, index) => {
      // Weight decreases further back in history
      const weight = Math.pow(this.DECAY_RATE, index);
      const impact = this.getSignalImpact(event.signal);

      currentScore += impact * weight;
      totalWeight += weight;
    });

    if (totalWeight === 0) return this.BASE_FACTOR;

    const averageImpact = currentScore / totalWeight;
    
    // Map average impact (-1 to 1) to Factor (MIN to MAX)
    // -1 -> MIN_FACTOR (0.5)
    // 0 -> BASE_FACTOR (1.0)
    // 1 -> MAX_FACTOR (1.5)
    
    let factor = 1.0 + (averageImpact * 0.5); // Simple linear mapping

    // Clamp
    return Math.max(this.MIN_FACTOR, Math.min(this.MAX_FACTOR, factor));
  }

  private static getSignalImpact(signal: string): number {
    switch (signal) {
      case 'positive_feedback': return 1.0;
      case 'complete': return 0.5;         // Completed = implicitly good
      case 'ignore': return -0.1;          // Ignored = slightly irrelevant
      case 'dismiss': return -0.8;         // Dismissed = annoying/wrong
      case 'negative_feedback': return -1.0;
      case 'correct': return 0.2;          // Correction is engagement, but mixed signal. Treat as slight positive for *relevance* (user cared to fix), but distinct from 'complete'.
      default: return 0;
    }
  }
}
