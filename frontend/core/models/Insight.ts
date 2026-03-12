export type InsightType = 'risk' | 'opportunity' | 'status';
export type InsightLevel = 'info' | 'warning' | 'critical' | 'success';

export interface Insight {
  id: string; // Unique ID for React keys
  type: InsightType;
  level: InsightLevel;
  title: string;
  explanation: string;
  recommendation: string;
  confidence: number; // 0.0 to 1.0
  riskIfIgnored?: string;
}
