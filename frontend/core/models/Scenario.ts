export type ScenarioId = 'healthy' | 'demo_fungal_risk' | 'demo_drought_stress';

export interface ScenarioDef {
  id: ScenarioId;
  name: string;
  description: string;
}
