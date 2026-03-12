import { FarmObject } from '../models/FarmObject';
import { Insight } from '../models/Insight';
import { ScenarioId } from '../models/Scenario';
import { TimeWindow } from '../models/TimeContext';

/**
 * PURE FUNCTION: Deterministically resolves insights based on world state.
 * No side effects. No APIs.
 */
export function resolveInsights(
  object: FarmObject | null,
  timeWindow: TimeWindow,
  scenarioId: ScenarioId | null
): Insight[] {
  if (!object || !scenarioId) {
    return [];
  }

  const insights: Insight[] = [];

  // --- SCENARIO: HEALTHY ---
  if (scenarioId === 'healthy') {
    insights.push({
      id: 'healthy-1',
      type: 'status',
      level: 'success',
      title: 'Optimal Conditions',
      explanation: 'Soil moisture and nutrient levels are within ideal ranges.',
      recommendation: 'Continue standard monitoring schedule.',
      confidence: 0.98
    });
  }

  // --- SCENARIO: FUNGAL RISK ---
  if (scenarioId === 'demo_fungal_risk') {
    if (timeWindow === 'today') {
      insights.push({
        id: 'fungal-early-1',
        type: 'risk',
        level: 'info',
        title: 'Elevated Humidity Detected',
        explanation: 'Recent rainfall and high temps created favorable conditions for fungal spores.',
        recommendation: 'Monitor lower leaves for lesions.',
        confidence: 0.75
      });
    } else if (timeWindow === '7d' || timeWindow === '30d') {
      insights.push({
        id: 'fungal-late-1',
        type: 'risk',
        level: 'warning',
        title: 'High Risk: Northern Corn Leaf Blight',
        explanation: 'Predictive models show 85% probability of outbreak based on current trajectory.',
        recommendation: 'Schedule fungicide application within 72 hours.',
        riskIfIgnored: 'Potential 15% yield loss in this sector.',
        confidence: 0.89
      });
    }
  }

  // --- SCENARIO: DROUGHT STRESS ---
  if (scenarioId === 'demo_drought_stress') {
    if (timeWindow === 'today') {
       insights.push({
        id: 'drought-early-1',
        type: 'risk',
        level: 'warning',
        title: 'Soil Moisture Depletion',
        explanation: 'Root zone moisture has dropped below 40%.',
        recommendation: 'Check irrigation pivots for blockages.',
        confidence: 0.8
      });
    } else if (timeWindow === '7d' || timeWindow === '30d') {
      insights.push({
        id: 'drought-late-1',
        type: 'risk',
        level: 'critical',
        title: 'Moisture Deficit Critical', // Stating facts, not emotions
        explanation: 'Projected moisture levels will inhibit crop synthesis within 5 days.', // "Inhibit synthesis" vs "Wilting point"
        recommendation: 'Initiate supplemental irrigation protocols.', // "Initiate supplemental" vs "Emergency protocols"
        riskIfIgnored: 'Significant yield variance projected.', // "Variance" vs "crop failure"
        confidence: 0.95
      });
    }
  }

  return insights;
}
