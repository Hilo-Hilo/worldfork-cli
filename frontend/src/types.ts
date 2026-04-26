export type View = 'landing' | 'big-bangs' | 'setup' | 'workspace' | 'reports' | 'report-view' | 'settings' | 'jobs';

export interface BigBang {
  id: string;
  name: string;
  description?: string | null;
  scenario_input: Record<string, unknown>;
  status: string;
  current_config_version: number;
  source_snapshot_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Multiverse {
  id: string;
  big_bang_id: string;
  parent_multiverse_id?: string | null;
  fork_tick_index?: number | null;
  ui_label: string;
  depth: number;
  status: string;
  branch_reason?: string | null;
  state: Record<string, unknown>;
  report_status: string;
  created_at: string;
  updated_at: string;
}

export interface LineageEdge {
  id?: string;
  parent_multiverse_id: string;
  child_multiverse_id: string;
  big_bang_id?: string;
  created_at?: string;
}

export interface TickSnapshot {
  id: string;
  big_bang_id: string;
  multiverse_id: string;
  tick_index: number;
  ui_label: string;
  status: string;
  provisional_bundle: Record<string, any>;
  final_bundle: Record<string, any>;
  summary?: string | null;
  artifact_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ActivityItem {
  kind: string;
  id: string;
  label: string;
  status: string;
  created_at?: string | null;
}

export interface Job {
  id: string;
  job_type: string;
  status: string;
  big_bang_id?: string | null;
  payload: Record<string, any>;
  result: Record<string, any>;
  error?: string | null;
  idempotency_key?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScenarioBankItem {
  id: string;
  title?: string;
  category?: string;
  fictionalization?: string;
  duration?: string;
  tick_size?: string;
  initial_public_event?: string;
  main_actors?: string[] | string;
  initial_cohorts?: string[] | string;
  public_channels?: string[] | string;
  branch_triggers?: string[] | string;
  expected_reports_questions?: string[] | string;
  tests?: string[] | string;
  expected_reports?: string[] | string;
  what_it_tests?: string;
  description?: string;
}

export interface BootstrapPayload {
  settings: {
    app_name: string;
    api_prefix: string;
    default_llm_provider: string;
    default_model: string;
  };
  defaults: {
    simulation_config: {
      tick_duration: string;
      max_ticks: number;
    };
    branch_policy: {
      max_branch_depth: number;
      max_active_multiverses: number;
      max_branches_per_tick: number;
      branch_score_threshold: number;
    };
    model_config: Record<string, string>;
  };
  labels: {
    emotions: unknown[];
    graph_layers: unknown[];
    sociology_models: unknown[];
    event_types: unknown[];
    social_action_types: unknown[];
    tools: unknown[];
  };
  scenario_bank: {
    scenarios: ScenarioBankItem[];
    coverage_matrix: Record<string, unknown>;
  };
  job_types: string[];
}

export interface WorkspaceTruncation {
  ticks_source_limit: number;
  latest_ticks_limit: number;
  total_ticks: number;
  ticks_source_truncated: boolean;
  latest_ticks_truncated: boolean;
}

export interface WorkspacePayload {
  big_bang: BigBang;
  multiverses: Multiverse[];
  lineage_edges: LineageEdge[];
  ticks_by_multiverse: Record<string, TickSnapshot[]>;
  latest_ticks: TickSnapshot[];
  actors: any[];
  graphs: {
    layers: Array<{ layer: string; count: number; latest_tick_index: number | null }>;
    snapshots: any[];
    influence_summary?: any;
    trait_vectors?: any[];
  };
  emotion_observability: {
    emotions_seen: string[];
    snapshots: any[];
    observations: any[];
  };
  sociology: {
    models_seen: string[];
    signals: any[];
    prompt_influences?: any[];
  };
  reports: any[];
  jobs: any[];
  activity: ActivityItem[];
  truncation: WorkspaceTruncation;
}

export interface BigBangCreatePayload {
  name: string;
  description?: string | null;
  scenario_text: string;
  simulation_config: Record<string, unknown>;
  branch_policy: Record<string, unknown>;
  use_initializer_agent: boolean;
  initializer_prompt?: string | null;
}
