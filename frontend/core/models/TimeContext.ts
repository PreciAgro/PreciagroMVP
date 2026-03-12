export type TimeWindow = 'today' | '7d' | '30d' | 'season' | 'multi-season';

export interface TimeContext {
  window: TimeWindow;
  // In a real app, this might include specific start/end dates,
  // but for Phase 2/Simulations, the "window" is the primary driver.
}
