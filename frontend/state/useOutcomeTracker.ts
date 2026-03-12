import { useLearningStore } from './useLearningStore';
import { OutcomeSignal } from '../core/models/Outcome';

export const useOutcomeTracker = () => {
  const recordOutcome = useLearningStore((state) => state.recordOutcome);

  const trackDismissal = (contentKey: string, featureId: string = 'insight-card') => {
    recordOutcome('dismiss', featureId, contentKey);
  };

  const trackCompletion = (contentKey: string, featureId: string = 'action-flow') => {
    recordOutcome('complete', featureId, contentKey);
  };

  const trackCorrection = (contentKey: string, correctionValue: string, featureId: string = 'insight-card') => {
    recordOutcome('correct', featureId, contentKey, correctionValue);
  };
  
  const trackPositiveFeedback = (contentKey: string, featureId: string) => {
    recordOutcome('positive_feedback', featureId, contentKey);
  }

  const trackNegativeFeedback = (contentKey: string, featureId: string) => {
    recordOutcome('negative_feedback', featureId, contentKey);
  }

  return {
    trackDismissal,
    trackCompletion,
    trackCorrection,
    trackPositiveFeedback,
    trackNegativeFeedback
  };
};
