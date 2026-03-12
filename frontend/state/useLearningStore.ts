import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { LearningEngine } from '../core/intelligence/LearningEngine';
import { OutcomeEvent, OutcomeSignal, CalibrationFactor } from '../core/models/Outcome';

interface LearningState {
  outcomeHistory: OutcomeEvent[];
  calibrations: Record<string, CalibrationFactor>;

  recordOutcome: (signal: OutcomeSignal, featureId: string, contentKey: string, correctionValue?: string) => void;
  getCalibration: (contentKey: string) => number;
  getExplanation: (contentKey: string) => string | null;
}

export const useLearningStore = create<LearningState>()(
  persist(
    (set, get) => ({
      outcomeHistory: [],
      calibrations: {},

      recordOutcome: (signal, featureId, contentKey, correctionValue) => {
        const newEvent: OutcomeEvent = {
          id: crypto.randomUUID(),
          signal,
          context: {
            featureId,
            contentKey,
            timestamp: new Date().toISOString()
          },
          correctionValue
        };

        set((state) => {
          const updatedHistory = [newEvent, ...state.outcomeHistory];
          
          // Re-calibrate specific content key
          const relevantHistory = updatedHistory.filter(e => e.context.contentKey === contentKey);
          const newFactor = LearningEngine.calculateCalibration(relevantHistory);

          const newCalibration: CalibrationFactor = {
            contentKey,
            factor: newFactor,
            lastUpdated: new Date().toISOString(),
            sampleSize: relevantHistory.length
          };

          return {
            outcomeHistory: updatedHistory,
            calibrations: {
              ...state.calibrations,
              [contentKey]: newCalibration
            }
          };
        });
      },

      getCalibration: (contentKey) => {
        const cal = get().calibrations[contentKey];
        if (!cal) return 1.0;
        return cal.factor;
      },

      getExplanation: (contentKey) => {
        const cal = get().calibrations[contentKey];
        if (!cal || cal.factor === 1.0) return null;

        if (cal.factor > 1.1) return "Increased priority based on your frequent usage.";
        if (cal.factor < 0.9) return "lowered priority based on previous dismissals.";
        
        return null;
      }
    }),
    {
      name: 'preciagro-learning-storage',
      storage: createJSONStorage(() => localStorage), 
    }
  )
);
