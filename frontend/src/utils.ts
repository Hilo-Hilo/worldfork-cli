import type { ScenarioBankItem, TickSnapshot } from './types';

export function compactId(value?: string | null): string { return value ? value.slice(0, 8) : 'none'; }
export function plural(count: number, word: string): string { return `${count} ${word}${count === 1 ? '' : 's'}`; }
export function statusClass(value?: string): string { return String(value || 'draft').toLowerCase().replace(/[^a-z0-9_-]/g, '-'); }
export function firstWords(value: unknown, count = 18): string {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  if (!text) return 'No summary yet.';
  const words = text.split(' ');
  return words.length > count ? `${words.slice(0, count).join(' ')}...` : text;
}
export function fmtDate(value?: string | null): string {
  if (!value) return 'not recorded';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}
export function tickCount(tick: TickSnapshot | undefined, key: string): number {
  if (!tick) return 0;
  const finalBundle = tick.final_bundle || {};
  const provisional = tick.provisional_bundle || {};
  const value = finalBundle[key] || provisional[key] || finalBundle.executed_events || provisional.executed_events || [];
  return Array.isArray(value) ? value.length : Number(value || 0);
}
export function listText(value: unknown): string {
  return Array.isArray(value) ? value.join(', ') : String(value || '');
}
function hasScenarioValue(value: unknown): boolean {
  return Array.isArray(value) ? value.length > 0 : Boolean(String(value || '').trim());
}
export function scenarioText(scenario: ScenarioBankItem): string {
  const expectedReports = scenario.expected_reports_questions ?? scenario.expected_reports;
  const tests = scenario.tests ?? scenario.what_it_tests;
  return [
    `Scenario title: ${scenario.title || scenario.id}`,
    scenario.duration ? `Simulation duration: ${scenario.duration}` : '',
    scenario.tick_size ? `Tick size: ${scenario.tick_size}` : '',
    scenario.initial_public_event ? `Initial public event: ${scenario.initial_public_event}` : '',
    scenario.main_actors ? `Main actors/heroes: ${listText(scenario.main_actors)}` : '',
    scenario.initial_cohorts ? `Initial cohorts: ${listText(scenario.initial_cohorts)}` : '',
    scenario.public_channels ? `Public channels: ${listText(scenario.public_channels)}` : '',
    scenario.branch_triggers ? `Branch triggers: ${listText(scenario.branch_triggers)}` : '',
    hasScenarioValue(expectedReports) ? `Expected reports/questions: ${listText(expectedReports)}` : '',
    hasScenarioValue(tests) ? `Tests: ${listText(tests)}` : '',
  ].filter(Boolean).join('\n');
}
