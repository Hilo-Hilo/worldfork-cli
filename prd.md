# WorldFork Full V1 Simulation Platform Specification

**Version:** 3.3 — full V1 simulation platform + progressive-disclosure UI + revised God Agent/tool-call architecture  
**Document type:** Simulation platform specification + implementation issue spec  
**Primary backend language:** Python  
**Primary database:** PostgreSQL  
**Canonical source of truth:** PostgreSQL for platform state and metadata; artifact store for large/raw payloads referenced from PostgreSQL  
**Default LLM routing provider:** OpenRouter, configurable per Big Bang  
**UI direction:** simple personal research/workbench interface with progressive disclosure, not enterprise/admin software  
**V1 framing:** This is intentionally a full V1 simulation platform, not a minimal prototype. Scope should be implemented in milestones, but the target product is the complete recursive simulation workbench described here.  
**V1 exclusions:** no enterprise billing, no team/admin roles, no external memory-service requirement, no hidden model-state steering, no generic enterprise dashboard, no mandatory human-operator intervention workflow in the primary loop.

---

## 0. Executive Summary

WorldFork is a personal recursive simulation platform for exploring how one scenario branches into many possible social futures.

A user creates a **Big Bang**. A Big Bang is the root scenario and owns one workspace. Inside that workspace, the user watches multiple **multiverse timelines** evolve over **ticks**. A timeline can branch recursively at any tick. A child timeline can branch again. Every branch is inspectable through logs, event summaries, cohort and hero decisions, social-media actions, sociology signals, graph changes, emotion-observability graphs, God Agent decisions, and reports.

The product must be visually simple even though the underlying simulation is deep. The UI uses **progressive disclosure**:

1. The default experience shows only the essential simulation surfaces.
2. Advanced details are available through expanders, drawers, filters, and detail panes.
3. Raw artifacts are available only behind explicit debug/advanced affordances.
4. The workspace must feel like a personal research workbench, not an enterprise control center.

The full V1 platform must include:

- Big Bang creation and selection;
- one workspace per Big Bang;
- recursive multiverse timelines;
- tick-level simulation;
- cohort and hero actors;
- event queues and event summaries;
- social-media/OASIS action surface as an input/event layer;
- versioned single-source-of-truth taxonomies;
- dependency, exposure, trust, influence, coalition, conflict, and OASIS interaction graph layers;
- sociology models for opinion drift, public silence, mobilization, homophily, complex contagion, social identity, and attention decay;
- observability-only emotion graphs that are parsed, stored, and visualized but not fed back into future agent prompts;
- a God Agent that reviews every tick, authorizes branches, approves/rejects split and emergence decisions, drives merge decisions through tool calls, and can terminate or freeze timelines;
- per-multiverse reports and a final Big Bang condensation report.

---

## 1. Product Goals

### 1.1 Primary Goal

Let one user create a scenario and inspect how it recursively branches through time while understanding why every branch, event, cohort shift, graph change, sociology signal, and report conclusion happened.

### 1.2 Core User Experience

The user should be able to:

1. open a minimal landing page;
2. click **Start Simulation**;
3. create or select a Big Bang;
4. enter a workspace dedicated to exactly one Big Bang;
5. watch timelines branch recursively over ticks;
6. click a timeline line to inspect that multiverse;
7. click a tick to inspect events, social-media actions, graph changes, sociology signals, and structured reasoning traces;
8. click an event to inspect what happened, who triggered it, why it happened, and what changed;
9. inspect dependency, exposure, trust, influence, coalition, conflict, and OASIS interaction graph layers;
10. inspect emotion-observability graphs without those emotion values steering future prompts;
11. read one report per terminated multiverse;
12. read a final Big Bang report after all multiverses terminate.

### 1.3 V1 Non-Goals

The full V1 simulation platform should not include:

- enterprise billing;
- team management;
- generic admin dashboards;
- external memory-service requirements;
- hidden activation/model-state steering;
- decorative UI screens that do not support simulation review;
- a generic “all projects dashboard” as the central experience;
- mandatory human-operator intervention as part of the primary tick loop.

Human intervention, rerun-from-checkpoint, operator annotations, and manual invalidation workflows are valuable future features, but the primary V1 control authority is the God Agent plus deterministic validation engines.

---

## 2. Core Hierarchy

WorldFork uses this hierarchy:

```text
BigBang
  └── MultiverseTimeline
        └── Tick
              ├── ActorStateSnapshot
              ├── CohortStateSnapshot
              ├── HeroStateSnapshot
              ├── EventLog
              ├── EventRevision
              ├── EventSummary
              ├── SocialMediaLog
              ├── OASISActionLog
              ├── ToolCallLog
              ├── CohortSplitCandidate
              ├── CohortMergeCandidate
              ├── CohortEmergenceCandidate
              ├── EmotionObservation
              ├── EmotionGraphSnapshot
              ├── SocialGraphDelta
              ├── SociologySignal
              ├── SociologyPromptInfluence
              ├── ReasoningTrace
              └── GodAgentReview
```

### 2.1 Big Bang

A Big Bang is the root scenario. One workspace views one and only one Big Bang.

A Big Bang contains:

- scenario input;
- source-of-truth snapshot;
- model config snapshot;
- simulation config;
- initial actor registry;
- initial population archetypes;
- initial cohort state nodes;
- hero archetypes;
- channels / social-media surfaces;
- all multiverse timelines;
- all reports;
- all artifacts.

### 2.2 Multiverse Timeline

A multiverse timeline is one possible path through the scenario.

A timeline may:

- continue to next tick;
- branch into one or more child timelines;
- freeze;
- terminate;
- complete and generate a report.

Branching is authorized by the God Agent and persisted by the multiverse/branch engine.

### 2.3 Tick

A tick is the smallest atomic simulation unit.

Tick duration is user-configurable per Big Bang. Examples:

- 1 hour;
- 2 hours;
- 1 day;
- 1 week.

Every prompt packet must include a human-readable time translation:

```text
Current tick: T7
Tick duration: 2 hours
Elapsed since Big Bang: 14 hours
Elapsed since previous tick: 2 hours
This event is scheduled for T10, which is 6 simulated hours from now.
```

### 2.4 Canonical IDs vs User-Facing Labels

The UI should use human-intuitive labels such as `M1.1:T7`.

PostgreSQL should store canonical IDs as UUIDs and lineage references. Canonical IDs are not exposed as the main user-facing identity in the UI.

User-facing labels are materialized from lineage and tick index.

Required distinction:

```text
canonical_tick_snapshot_id: UUID, internal/database/API identity
ui_tick_label: M1.1:T7, human-facing display label
canonical_multiverse_id: UUID, internal/database/API identity
ui_multiverse_label: M1.1, human-facing display label
```

The UI should never make the user reason about internal UUIDs unless they explicitly open a debug/raw artifact view.

---

## 3. Single Source of Truth System

Single-source-of-truth files are mandatory.

The system must never hardcode emotion names, behavior axes, expression scale descriptions, event types, social action types, graph layer labels, or sociology model labels in arbitrary prompt text or business logic. These definitions must come from versioned source-of-truth files.

### 3.1 Required Folder

```text
source_of_truth/
  emotions.json
  behavior_axes.json
  ideology_axes.json
  issue_stance_axes.json
  expression_scale.json
  event_types.json
  social_action_types.json
  graph_edge_types.json
  sociology_models.json
  sociology_presets.json
  cohort_state_schema.json
  hero_state_schema.json
  actor_schema.json
  tool_registry.json
  report_templates/
    event_summary.md
    tick_summary.md
    multiverse_report.md
    final_big_bang_report.md
  god_agent_policy.json
```

### 3.2 Snapshot Rule

When a Big Bang is created, copy the complete source-of-truth folder into the Big Bang artifact folder and persist the snapshot metadata in PostgreSQL:

```text
artifacts/big_bang_<id>/configs/source_of_truth/
```

Historical Big Bangs must not change when global source-of-truth files are edited later.

PostgreSQL must store:

- snapshot ID;
- source-of-truth version;
- content hash;
- artifact path;
- created timestamp;
- associated Big Bang ID.

### 3.3 `emotions.json`

Emotion graphs use explicit prompt/state values only for observability. They do not use hidden model-state control.

Scale:

```text
0 = absent / not expressed
5 = moderate
10 = extreme / dominant
```

V1 emotions:

- anger;
- fear;
- distrust;
- trust;
- hope;
- calm;
- confusion;
- urgency;
- sympathy;
- resentment.

Each emotion entry must include:

- `id`;
- `label`;
- `definition`;
- anchors for `0`, `5`, and `10`;
- prompt guidance for self-rating output;
- UI color.

Important rule:

> Emotion values are parsed, stored, graphed, and reported as observability data. They are not fed back into future agent prompts and are not used as canonical actor state.

### 3.4 `behavior_axes.json`

Required axes:

- stubbornness;
- openness_to_change;
- evidence_sensitivity;
- source_credulity;
- authority_deference;
- contrarianism;
- sycophancy;
- risk_tolerance;
- coordination_capacity;
- mobilization_capacity;
- attention_decay_rate;
- media_susceptibility;
- spiral_silence_susceptibility;
- identity_salience_sensitivity;
- analytical_depth.

### 3.5 `ideology_axes.json`

Minimum axes:

- economic axis: redistributive/state-interventionist ↔ market-oriented/pro-capital;
- cultural axis: progressive/cosmopolitan ↔ traditionalist/communitarian;
- governance axis: libertarian/decentralized ↔ authoritarian/centralized;
- tech axis: precautionary/safety-first ↔ accelerationist/innovation-first;
- institutional trust axis: anti-institutional ↔ institution-trusting.

### 3.6 `expression_scale.json`

Expression level is a `0–1` scale used for public visibility, speaking probability, and action intensity.

Recommended anchors:

- `0.00–0.10`: negligent / unaware;
- `0.10–0.25`: silent observer;
- `0.25–0.40`: low-level discussant;
- `0.40–0.60`: active speaker;
- `0.60–0.75`: advocate;
- `0.75–0.90`: organizer;
- `0.90–1.00`: high-risk escalator.

The simulator may model escalation risk categorically, but must not generate tactical instructions for violence.

### 3.7 `graph_edge_types.json`

Required edge types:

- `exposure` — actor A sees actor B’s content;
- `trust` — actor A treats actor B as credible;
- `dependency` — actor A materially/institutionally depends on actor B;
- `influence` — actor A can change actor B’s reach, incentives, or action options;
- `coalition` — actor A coordinates with actor B;
- `conflict` — actor A opposes actor B;
- `oasis_interaction` — platform-level social action edge.

### 3.8 `sociology_models.json`

Required model registry:

- bounded confidence / anchored opinion drift;
- Granovetter-style threshold mobilization;
- spiral of silence;
- homophily / adaptive exposure;
- complex contagion;
- social identity salience;
- attention decay / agenda setting.

---

## 4. Actor Model

WorldFork uses a unified actor abstraction so cohorts, heroes, institutions, media channels, platform surfaces, and external entities can all participate in events, graph edges, posts, reasoning traces, and reports.

### 4.1 Actor

An actor is any simulation entity that can appear in logs, events, graph edges, posts, tool calls, or reports.

Required fields:

```text
actors
  actor_id UUID primary key
  big_bang_id UUID
  actor_type text  -- cohort | hero | institution | media_channel | platform | external_entity
  display_name text
  canonical_ref_type text null
  canonical_ref_id UUID null
  description text null
  created_tick_index int null
  status text
  created_at timestamptz
```

Actor IDs are the consistent reference point for:

- events;
- social posts;
- graph edges;
- reasoning traces;
- tool calls;
- sociology signals;
- reports;
- emotion observations.

### 4.2 Population Archetype

A population archetype is a stable description of a population over a short-to-mid-term simulation horizon.

Target horizon:

```text
1 week to 2 years
```

Mostly stable fields:

- geography;
- age band;
- education profile;
- socioeconomic profile;
- occupation or role;
- institution membership;
- cultural tags;
- baseline ideology axes;
- baseline behavior axes;
- baseline media diet;
- baseline trust priors;
- baseline issue relevance;
- total population estimate.

Do not put highly mutable values here, such as current anger, current support, current event queue, or current posts.

### 4.3 Cohort State Node

A cohort state node is a mutable slice of a population archetype inside one multiverse at one point in time.

Example:

```text
Population archetype:
  UC Berkeley center-left students

Cohort state nodes:
  neutral / silent / 600 people
  oppose / active speaker / 300 people
  oppose / organizer / 100 people
```

Required mutable fields:

- `cohort_state_id`;
- `actor_id`;
- `archetype_id`;
- `multiverse_id`;
- `tick_index`;
- `represented_population`;
- `stance_axes`;
- `expression_level`;
- `attention_level`;
- `fatigue`;
- `perceived_majority`;
- `fear_of_isolation`;
- `mobilization_readiness`;
- `trust_summary`;
- `dependency_summary`;
- `recent_post_ids`;
- `queued_event_ids`;
- `recent_reasoning_trace_ids`;
- `sociology_prompt_influence_ids`.

Removed from canonical cohort state:

- current numeric emotion values.

Emotion self-ratings are still collected and graphed, but they are observability-only data and must not be fed into future prompts.

### 4.4 Hero Archetype

A hero archetype represents one influential individual or a very small number of individuals.

Heroes are not cohorts. They do not represent a large population. They are high-impact agents with outsized ability to trigger social or political consequences.

Examples:

- a president;
- a CEO;
- a founder;
- a major journalist;
- a protest leader;
- a regulator;
- a celebrity influencer.

Required fields:

- `hero_id`;
- `actor_id`;
- `display_name`;
- `role`;
- `institution`;
- `public_reach`;
- `institutional_power`;
- `financial_power`;
- `agenda_control`;
- `media_access`;
- `baseline_ideology_axes`;
- `baseline_behavior_axes`;
- `volatility`;
- `ego_sensitivity`;
- `strategic_discipline`;
- `controversy_tolerance`;
- `direct_event_power`.

Removed from canonical hero archetype/state:

- baseline numeric emotion profile;
- current numeric emotions.

Hero affect can still be inferred for observability graphs, but it should not become prompt-driving state.

### 4.5 Hero State

Hero state is mutable per tick and per multiverse.

Fields:

- `hero_state_id`;
- `actor_id`;
- `multiverse_id`;
- `tick_index`;
- current stance;
- attention;
- fatigue;
- perceived pressure;
- current strategy;
- queued events;
- recent posts;
- reasoning traces;
- sociology prompt influence IDs.

---

## 5. Landing Page and Big Bang Flow

### 5.1 Landing Page

The landing page should be extremely simple.

Required content:

```text
WorldFork
Simulate one scenario across many branching futures.

Create a Big Bang, watch timelines fork over time, and inspect exactly why each event, cohort shift, and branch happened.

[Start Simulation]
[View Past Big Bangs]
```

No enterprise cards. No admin/product suite framing.

### 5.2 Big Bangs Page

Route:

```text
/big-bangs
```

Purpose:

- select an existing Big Bang;
- create a new Big Bang;
- view recent sessions.

Allowed edits:

- rename Big Bang;
- archive Big Bang;
- duplicate Big Bang config.

Not allowed:

- mutate historical tick logs in place;
- rewrite event logs in place;
- edit completed reports in place.

All meaningful mutations create new versions or append-only revisions.

### 5.3 New Big Bang Page

Route:

```text
/big-bangs/new
```

Required setup fields:

- scenario prompt;
- optional documents;
- tick duration;
- max ticks;
- initial root timelines;
- max branch depth;
- max active multiverses;
- max branches per tick;
- branch score threshold;
- source-of-truth snapshot selection;
- model configs;
- report agent configs;
- God Agent settings;
- social media/OASIS settings;
- sociology preset;
- emotion graph observability settings;
- dependency graph settings.

After creation, route to:

```text
/workspace/{big_bang_id}
```

---

## 6. Workspace UI: Progressive Disclosure

### 6.1 Route

```text
/workspace/{big_bang_id}
```

A workspace views exactly one Big Bang.

### 6.2 Design Principle

The simulation platform is deep, but the UI should not expose all complexity at once.

Default UI principle:

> Show the timeline, the selected object, and the most important explanation first. Hide specialist panels behind expansion, filters, drawers, and advanced mode.

### 6.3 Workspace Layout

```text
┌───────────────────────────────────────────────────────────────┐
│ Top bar: Big Bang name, status, clock, primary controls        │
├───────────────────────────────────────────────┬───────────────┤
│ Center Pane                                    │ Inspector     │
│ Recursive multiverse graph                     │ Contextual    │
│                                                │ details       │
├───────────────────────────────────────────────┴───────────────┤
│ Tick Detail Drawer / Bottom Pane, hidden until opened          │
└───────────────────────────────────────────────────────────────┘
```

Default proportions:

- center pane: 65–75%;
- inspector pane: 25–35%;
- bottom/tick drawer: hidden until opened, then 35–45% of viewport height.

Optional activity drawer:

- can slide in from the left;
- defaults to collapsed;
- shows recent activity, filters, and search.

Panes should be resizable.

### 6.4 Top Bar

Default controls:

- Big Bang name;
- status;
- current simulated time;
- active timeline count;
- Start / Pause / Step Tick;
- Reports;
- Settings.

Advanced controls are hidden under an **Overlays** or **View Options** menu:

- Emotion Graph overlay;
- Dependency Graph overlay;
- Sociology Overlay;
- Raw Artifact debug mode;
- Graph layer selector;
- lineage focus toggle.

### 6.5 Inspector Pane

The inspector pane replaces always-visible left/right tab sprawl.

Default state:

- Big Bang summary;
- latest important activity;
- current simulation status;
- recent God Agent decisions;
- report progress.

When a timeline is selected:

- selected multiverse ID;
- parent timeline;
- fork tick;
- recent ticks;
- most recent events;
- recent sociology signals;
- report status;
- controls: focus lineage, open report, simulate next tick, terminate timeline.

When a tick is selected:

- tick summary;
- event count;
- post count;
- graph changes;
- sociology highlights;
- God Agent end-of-tick decision;
- button to open full tick detail drawer.

When an event is selected:

- event summary;
- who triggered it;
- why it happened;
- affected actors;
- related posts;
- related graph changes;
- related sociology signals;
- event summary version history.

### 6.6 Advanced Detail Panels

Advanced panels are available through expanders or drawers, not as always-visible tab sets.

Advanced panels include:

1. Social Media;
2. OASIS Actions;
3. Queued Events;
4. Tool Calls;
5. Cohorts;
6. Splits / Merges / Emergence;
7. Emotion Observability Graphs;
8. Dependency / Multiplex Graphs;
9. Sociology Signals;
10. Raw Artifacts.

### 6.7 Bottom Tick Detail Drawer

The bottom pane opens when the user clicks a tick or selects “Open full tick detail.”

Default tab:

1. Overview.

Expandable sections:

2. Cohort and Hero Traces;
3. Events;
4. Social Media;
5. Tool Calls;
6. Splits / Merges / Emergence;
7. Emotion Observability Graphs;
8. Dependency and Multiplex Graphs;
9. Sociology Signals;
10. Raw Artifacts.

The UI should initially show the Overview and top explanation, then let the user drill down.

---

## 7. Center Pane: Recursive Multiverse Graph

This is the primary screen.

### 7.1 Required Visual Behavior

The graph must show:

- Big Bang root node on the left;
- horizontal tick axis;
- each timeline as a horizontal rail;
- tick boxes on each rail;
- fork points;
- recursive child branches;
- collapsed child counts when too many branches exist;
- status color per timeline;
- timeline labels such as `M1`, `M1.1`, `M1.2.1`;
- tick labels such as `M1.1:T7`.

### 7.2 Recursive Branching Rule

Branching is recursive:

```text
M1
  ├── M1.1
  │     ├── M1.1.1
  │     └── M1.1.2
  └── M1.2
        └── M1.2.1
```

Every child timeline can branch again.

### 7.3 Display Label Rule

If `M1` forks at `T7` into `M1.1`:

- `M1` continues as `M1:T8`, `M1:T9`, etc.;
- `M1.1` displays inherited parent history as `M1.1:T0` through `M1.1:T7`;
- `M1.1:T8` and onward are native child ticks.

Storage must not rewrite parent tick rows. The UI materializes display labels through lineage references.

### 7.4 Tick Box Content

Each tick box shows:

```text
M1.1:T7
status dot
#events
#posts
#tool calls
branch marker if applicable
```

Hover shows:

- simulated time;
- summary;
- top events;
- active cohorts/heroes;
- social posts count;
- branch trigger if applicable;
- major graph changes if available;
- sociology model highlights if available;
- emotion-observability deltas if available.

Click opens the tick detail drawer.

### 7.5 Timeline Click Behavior

Clicking a timeline line should:

- select that multiverse;
- update inspector pane to show timeline details;
- highlight lineage path;
- dim unrelated timelines;
- show recent graph changes and sociology signals;
- offer a link to the multiverse report when available.

### 7.6 Overlay Modes

The center pane supports optional overlays:

1. **Emotion Observability Overlay**
   - small trend bands or sparklines along timeline rails;
   - shows explicit observed emotion values from `emotions.json`;
   - must be labeled as observability-only.

2. **Dependency Overlay**
   - highlights dependency stress or key dependency edges relevant to selected timeline/tick.

3. **Sociology Overlay**
   - marks ticks where sociology models triggered major changes.

4. **Graph Layer Overlay**
   - lets users choose exposure, trust, dependency, influence, coalition, conflict, or OASIS interaction layers.

---

## 8. Activity, Social Media, and OASIS UI

### 8.1 Activity Drawer

The activity drawer is collapsed by default.

When opened, it shows Big Bang-level or multiverse-scoped activity:

- recent social-media logs;
- recent OASIS actions;
- recent queued events;
- recent tool calls;
- latest cohort splits/merges/emergences;
- latest God Agent actions;
- latest emotion-observability graph changes;
- latest graph edge changes;
- latest sociology signals.

The drawer should support filters instead of exposing many tabs by default.

### 8.2 Social Media Panel

Shows:

- posts;
- replies;
- reposts;
- likes/upvotes;
- quote posts;
- channel source;
- author actor;
- tick created;
- reach/amplification.

### 8.3 OASIS Actions Panel

Action types:

- `post`;
- `comment`;
- `reply`;
- `repost`;
- `quote`;
- `like`;
- `upvote`;
- `downvote`;
- `follow`;
- `unfollow`;
- `search`;
- `mute`;
- `do_nothing`.

### 8.4 Social Layer Boundary

The social-media/OASIS layer is an input and event surface. It does not own core population state.

It emits:

- posts;
- comments;
- follows;
- feed visibility observations;
- amplification observations;
- social actions;
- possible event triggers.

The core simulation engine owns and applies state changes to:

- Big Bangs;
- multiverse lineage;
- cohort state;
- hero state;
- event queues;
- God Agent decisions;
- reports;
- graph layers;
- sociology signals;
- emotion-observability graphs.

---

## 9. Reasoning Traces, Raw Artifacts, and Visibility

### 9.1 Reasoning Trace Policy

Use structured explainability, not raw private chain-of-thought.

Reasoning traces are user-visible summaries of what the agent considered and chose. They are not meant to expose hidden deliberation or private chain-of-thought.

### 9.2 Reasoning Trace Format

Fields:

- trace ID;
- agent ID;
- agent type;
- actor ID if applicable;
- multiverse ID;
- tick;
- decision summary;
- inputs considered;
- tool calls used;
- selected action;
- confidence;
- short rationale;
- sanitized prompt artifact link;
- sanitized response artifact link;
- raw prompt artifact link, debug-only;
- raw response artifact link, debug-only;
- redaction status;
- visibility level.

### 9.3 Raw Artifact Safety

Raw prompt and raw response artifacts are valuable for debugging, audit, and reproducibility, but they may contain:

- long unstructured model output;
- invalid JSON;
- unsafe content that was later rejected;
- prompt-injection attempts from input documents or simulated social posts;
- irrelevant hidden deliberation-like text;
- personally sensitive simulated material.

Therefore:

1. the default UI must show sanitized structured traces;
2. raw artifacts must be behind advanced/debug affordances;
3. raw artifacts must be linked from PostgreSQL metadata;
4. redaction and validation status must be visible;
5. raw artifacts should never be required for normal simulation review.

---

## 10. Event Logic and Versioning

### 10.1 Event Queue

Each multiverse has an event queue.

Events may be created by:

- cohorts;
- heroes;
- OASIS/social-media triggers;
- channels;
- God Agent;
- initialization agent.

### 10.2 Event Fields

- event ID;
- current revision ID;
- creator actor ID;
- event type;
- created tick;
- scheduled tick;
- status;
- title;
- description;
- preconditions;
- expected impact;
- actual impact;
- related posts;
- related graph edges;
- related sociology signals;
- related emotion-observability deltas.

### 10.3 Event Revisions

Events are append-only.

Editing an event creates an `event_revision`; it does not mutate the historical event row in place.

Required event revision fields:

```text
event_revisions
  id UUID primary key
  event_id UUID
  revision_number int
  edited_by_actor_id UUID null
  edited_by_agent_type text null
  edit_reason text
  title text
  description text
  scheduled_tick int
  preconditions jsonb
  expected_impact jsonb
  created_at timestamptz
```

### 10.4 Event Summary LLM Call

After every successfully executed event, run a summary call.

Inputs:

- event object;
- active event revision;
- creator reasoning trace;
- affected actors;
- relevant social posts;
- tool call history;
- local tick context;
- dependency graph context;
- sociology signals;
- emotion-observability observations, if available for reporting only.

Outputs:

- what happened;
- why it happened;
- who triggered it;
- what changed;
- what uncertainty remains;
- follow-up risks;
- links to related logs.

### 10.5 Event Summary Versions

Regenerating a summary creates a new `event_summary.version`.

Summaries are immutable by version. A newer version may supersede an older version, but old versions remain auditable.

---

## 11. Emotion Observability Graphs

Emotion graphs are required, but they are observability-only.

They are explicit time-series values derived from structured outputs and summaries. They are not hidden model-state features and are not fed back into future prompts.

### 11.1 Core Rule

Emotion values should be:

- requested as structured self-rating output;
- parsed;
- validated against `emotions.json`;
- stored as observations;
- graphed;
- used in reports as evidence;
- excluded from future agent prompt context;
- excluded from canonical cohort/hero state.

### 11.2 Data Sources

- cohort self-rating output;
- hero self-rating output;
- event summary inference;
- God Agent review inference for reporting;
- report agent aggregation.

### 11.3 Data Model

```text
emotion_observations
  id UUID primary key
  big_bang_id UUID
  multiverse_id UUID
  tick_snapshot_id UUID
  actor_id UUID
  emotion_key text
  value numeric  -- 0-10
  source text
  confidence numeric null
  related_event_id UUID null
  related_reasoning_trace_id UUID null
  explanation text null
  prompt_feedback_eligible boolean default false
  created_at timestamptz
```

`prompt_feedback_eligible` must default to `false` and should remain `false` for V1.

```text
emotion_graph_snapshots
  id UUID primary key
  big_bang_id UUID
  multiverse_id UUID
  tick_index int
  scope text
  scope_id text
  values_json jsonb
  source_observation_ids UUID[]
  created_at timestamptz
```

### 11.4 Update Logic

At the end of every tick, after the sociology engine has run:

1. collect agent self-reported values;
2. collect event-summary inferred values/deltas;
3. normalize values to source-of-truth scale;
4. write observations;
5. compute aggregate snapshots;
6. expose graph data to the UI;
7. do not add emotion values to future prompt packets.

---

## 12. Dependency and Multiplex Graphs

WorldFork uses multiple graph layers.

### 12.1 Required Layers

1. exposure graph;
2. trust graph;
3. dependency graph;
4. influence graph;
5. coalition graph;
6. conflict graph;
7. OASIS/social-media interaction graph.

### 12.2 Dependency Graph Meaning

Dependency edges represent material, institutional, economic, legal, or reputational dependence.

Examples:

- students depend on university administration;
- workers depend on employers;
- companies depend on regulators, investors, customers, and suppliers;
- politicians depend on voters, donors, parties, and media coverage;
- news channels depend on attention, credibility, access, and audience segment.

### 12.3 Graph Edge Data Model

```text
graph_edges
  id UUID primary key
  big_bang_id UUID
  multiverse_id UUID
  tick_index int
  graph_layer text
  source_actor_id UUID
  target_actor_id UUID
  weight numeric
  direction text
  reason text null
  evidence_event_id UUID null
  evidence_reasoning_trace_id UUID null
  status text
  created_at timestamptz
```

### 12.4 Graph Snapshot Data Model

```text
graph_snapshots
  id UUID primary key
  big_bang_id UUID
  multiverse_id UUID
  tick_index int
  graph_layer text
  artifact_id UUID null
  summary text null
  created_at timestamptz
```

---

## 13. Sociology Engine

The sociology engine converts posts, events, actor states, and graph exposure into interpretable state changes and prompt influences.

It runs before the emotion-observability graph update.

### 13.1 Sociology as Prompt Influence

The sociology engine can influence future agent behavior by producing explicit, inspectable prompt context.

Example prompt insertion:

```text
Sociology context for this actor:
- Perceived majority pressure: {perceived_majority_pressure}
- Silence pressure: {silence_pressure}
- Mobilization threshold status: {mobilization_threshold_status}
- Attention salience: {attention_salience}
- Identity salience: {identity_salience}
- Exposure/trust context: {exposure_trust_summary}

Take this sociology context into account when deciding how this cohort or hero responds this tick.
```

This is explicit simulation state, not hidden model-state steering.

Important boundary:

- sociology prompt influences may be inserted into future prompts;
- emotion graph values may not be inserted into future prompts.

### 13.2 Required Models

#### 13.2.1 Bounded Confidence + Anchored Opinion Drift

Purpose:

- model opinion drift;
- allow polarization and fragmentation;
- prevent unrealistic full convergence.

Reads:

- stance axes;
- confidence;
- stubbornness;
- trust edges;
- exposure edges;
- confidence radius.

Writes:

- updated stance;
- stance confidence;
- sociology signal;
- optional prompt influence for next tick.

#### 13.2.2 Granovetter-Style Threshold Mobilization

Purpose:

- determine when a cohort publicly acts;
- model protest, advocacy, posting, or event support thresholds.

Reads:

- visible peer support;
- grievance;
- fear of cost;
- perceived efficacy;
- expression level;
- mobilization capacity.

Writes:

- mobilization probability;
- action adoption signal;
- optional prompt influence for next tick.

#### 13.2.3 Spiral of Silence

Purpose:

- explain private support but public silence;
- model self-censorship and expression suppression.

Reads:

- perceived majority;
- fear of isolation;
- social cost;
- visible support;
- expression level.

Writes:

- public voice probability;
- expression suppression signal;
- optional prompt influence for next tick.

#### 13.2.4 Homophily and Adaptive Exposure

Purpose:

- model echo chambers;
- update who sees whom.

Reads:

- ideology similarity;
- identity similarity;
- trust similarity;
- media-diet similarity;
- feed affinity.

Writes:

- exposure edge updates;
- trust edge updates;
- cluster signals;
- optional prompt influence for next tick.

#### 13.2.5 Complex Contagion

Purpose:

- model high-cost behaviors requiring multiple trusted exposures.

Reads:

- distinct trusted sources;
- reinforcement count;
- action cost;
- coordination capacity;
- coalition graph.

Writes:

- adoption/non-adoption result;
- reinforcement signal;
- event support or cancellation;
- optional prompt influence for next tick.

#### 13.2.6 Social Identity Salience

Purpose:

- model in-group/out-group dynamics;
- amplify identity-linked behavior during threat.

Reads:

- identity tags;
- perceived outgroup threat;
- conflict graph;
- symbolic stakes;
- social pressure signals.

Writes:

- identity salience;
- confidence-radius adjustment;
- homophily adjustment;
- mobilization-threshold adjustment;
- optional prompt influence for next tick.

#### 13.2.7 Attention Decay / Agenda Setting

Purpose:

- model how long a group cares about an issue;
- model media and social-feed salience.

Reads:

- attention level;
- attention decay rate;
- event salience;
- media susceptibility;
- issue relevance.

Writes:

- updated attention level;
- salience shifts;
- attention-decay signal;
- optional prompt influence for next tick.

### 13.3 Sociology Update Order

Within a tick, sociology runs after agent actions/events are available and before emotion-observability graphs are updated.

Order:

1. compute exposure from visible feed and event logs;
2. update attention and salience;
3. update private stance;
4. apply spiral-of-silence expression gate;
5. evaluate mobilization thresholds;
6. evaluate complex contagion;
7. update graph layers;
8. apply social identity modifiers;
9. generate split candidates;
10. generate merge candidates through deterministic engine analysis only;
11. generate emergence candidates;
12. write sociology signals;
13. write sociology prompt influences for next tick;
14. pass signals and candidates to the God Agent;
15. run emotion-observability graph update after sociology completes.

### 13.4 Sociology Signals Data Model

```text
sociology_signals
  id UUID primary key
  big_bang_id UUID
  multiverse_id UUID
  tick_snapshot_id UUID null
  model_key text
  affected_actor_id UUID
  input_summary jsonb
  output_summary jsonb
  explanation text
  related_event_id UUID null
  related_graph_edge_ids UUID[]
  created_at timestamptz
```

### 13.5 Sociology Prompt Influence Data Model

```text
sociology_prompt_influences
  id UUID primary key
  big_bang_id UUID
  multiverse_id UUID
  tick_index int
  actor_id UUID
  model_key text
  prompt_summary text
  structured_values jsonb
  source_signal_ids UUID[]
  applies_to_tick_index int
  created_at timestamptz
```

Sociology prompt influences are the only sociology-derived material inserted into future prompts.

---

## 14. Cohort Split, Merge, and Emergence

### 14.1 Splits

A split happens when one cohort becomes too internally diverse to remain one state node.

Split triggers:

- stance distribution becomes bimodal;
- expression levels diverge;
- action disagreement is high;
- sociology engine detects different thresholds being crossed;
- LLM proposes a substantial minority faction;
- cohort/hero reasoning suggests a durable subgroup may exist.

Split pipeline:

```text
LLM/cohort/hero proposes split
  → engine validates invariants
  → God Agent approves or rejects
  → engine persists approved split
```

The engine validates:

- child populations sum to parent population;
- each child meets minimum population threshold;
- child states are semantically distinct;
- no duplicate cohort exists;
- split reason is linked to evidence.

### 14.2 Merges

A merge happens when sibling or similar cohorts become close enough.

Merge triggers:

- same archetype;
- similar stance;
- similar expression level;
- similar media diet;
- low divergence for several ticks;
- high overlap in graph position;
- high overlap in sociology prompt influences.

Merge proposal rule:

> LLMs, cohorts, and heroes do not propose merges.

Merge pipeline:

```text
engine detects merge candidates
  → God Agent reviews candidate
  → God Agent may call merge-planning tool with desired parameters
  → engine validates requested merge plan
  → God Agent approves/rejects validated plan or calls tool again with revised parameters
  → engine persists approved merge
```

The God Agent may request different weights, population allocations, stance values, expression values, or report-facing emotion-observability rollups. Emotion-observability rollups remain reporting/graph data and are not fed into future prompts.

### 14.3 Emergence

A new cohort may emerge when:

- multiple cohorts coordinate into a distinct movement;
- social media logs reveal a new public identity;
- an event creates a new affected population;
- a significant subgroup is too distinct to remain a child slice;
- the God Agent determines a durable group exists.

Emergence pipeline:

```text
LLM/cohort/hero/sociology engine proposes emergence candidate
  → engine validates invariants
  → God Agent approves or rejects durable emergence
  → engine persists approved emergence
```

Only the God Agent can approve durable new cohort emergence.

---

## 15. God Agent

The God Agent runs at the end of every tick for every active multiverse.

The God Agent is the primary V1 intervention and governance mechanism.

### 15.1 Authority

The God Agent may authorize or request:

1. continue the timeline;
2. terminate the timeline;
3. freeze the timeline;
4. create a new branch;
5. approve/reject a cohort split;
6. review and drive a cohort merge through tool calls;
7. approve/reject a new cohort emergence;
8. register a key event;
9. request event summary regeneration;
10. mark a timeline as ready for report generation.

### 15.2 Tool-Call Architecture

The God Agent does not directly mutate database state.

The God Agent emits structured tool calls. Tools validate and execute the requested operation.

Example tools:

- `continue_timeline`;
- `freeze_timeline`;
- `terminate_timeline`;
- `create_branch`;
- `approve_split`;
- `reject_split`;
- `plan_merge`;
- `approve_merge_plan`;
- `reject_merge_plan`;
- `approve_emergence`;
- `reject_emergence`;
- `register_key_event`;
- `request_event_summary_regeneration`;
- `mark_ready_for_report`.

For branching:

```text
God Agent emits create_branch tool call
  → branch/multiverse engine validates policy and budget
  → branch/multiverse engine creates child timeline
  → lineage references are persisted
  → workspace stream is notified
```

Precise wording:

> Only the God Agent may authorize a branch. Only the branch/multiverse engine may persist branch creation.

### 15.3 Inputs

- provisional tick bundle;
- recent tick snapshots;
- event summaries;
- social-media logs;
- OASIS action logs;
- tool calls;
- cohort split candidates;
- cohort merge candidates;
- cohort emergence candidates;
- emotion-observability graph changes;
- dependency/multiplex graph changes;
- sociology signals;
- branch policy;
- timeline budget;
- current multiverse health.

### 15.4 Outputs

The God Agent outputs:

- structured review record;
- one or more tool calls;
- decision rationale;
- confidence;
- affected timelines/cohorts/events;
- artifact links.

### 15.5 Restrictions

The God Agent must not rewrite historical tick artifacts.

All actions must be stored as explicit decisions with:

- input summary;
- decision;
- rationale;
- affected timelines/cohorts/events;
- sanitized prompt artifact;
- sanitized response artifact;
- raw prompt artifact, debug-only;
- raw response artifact, debug-only.

---

## 16. Recursive Branching Logic

### 16.1 Branch Trigger Inputs

- executed events;
- unstable decisions;
- high divergence score;
- high uncertainty;
- major cohort split or emergence;
- major graph change;
- major sociology signal;
- user-defined branch policy;
- model-configured branch budget.

Emotion-observability values may be displayed to the God Agent for reporting/explanation, but should not be used as canonical branch-driving state unless a future version explicitly enables that behavior.

### 16.2 Branch Creation Steps

1. God Agent emits `create_branch` tool call.
2. Branch/multiverse engine validates policy, idempotency key, and budget.
3. Branch/multiverse engine creates child timeline ID using recursive naming convention.
4. Store parent timeline and fork tick.
5. Create lineage references for inherited ticks.
6. Copy relevant current state into child native starting state.
7. Persist branch reason.
8. Notify workspace stream.

### 16.3 Branch Statuses

- `active`;
- `candidate`;
- `frozen`;
- `terminated`;
- `completed`;
- `failed`.

### 16.4 Branch Explosion Controls

Recursive branching must include controls:

- max branch depth;
- max active multiverses;
- max branches per tick;
- branch score threshold;
- duplicate branch suppression;
- auto-freeze low-value timelines;
- configurable branch budget;
- idempotency keys for branch creation.

---

## 17. Main Tick Loop

The tick loop must preserve the rule that the God Agent runs at the end of every tick.

The sociology engine must run before the emotion-observability graph update.

```python
async def run_tick(multiverse_id: UUID, tick_index: int):
    lock(multiverse_id, tick_index)

    clock_context = build_clock_context(multiverse_id, tick_index)
    current_state = load_current_state(multiverse_id, tick_index)
    prior_sociology_prompt_influences = load_prompt_influences_for_tick(
        multiverse_id,
        tick_index,
    )

    # Emotion graph values are intentionally not loaded into prompt context.
    prompt_context = build_agent_prompt_context(
        clock_context=clock_context,
        current_state=current_state,
        sociology_prompt_influences=prior_sociology_prompt_influences,
    )

    due_events = load_due_events(multiverse_id, tick_index)
    visible_social_context = build_social_context(multiverse_id, tick_index)
    active_agents = select_active_cohorts_and_heroes(multiverse_id, tick_index)

    agent_outputs = await run_agent_decisions(active_agents, prompt_context, visible_social_context)
    parsed_actions = validate_agent_outputs(agent_outputs)
    emotion_self_ratings = parse_emotion_self_ratings_for_observability(agent_outputs)

    social_observations = apply_social_actions_as_input_surface(parsed_actions)
    queue_or_version_events(parsed_actions)
    executed_events = execute_due_events(due_events)

    event_summaries = await summarize_executed_events(executed_events)

    state_update_candidates = derive_state_update_candidates(
        parsed_actions,
        executed_events,
        event_summaries,
        social_observations,
    )

    sociology_result = run_sociology_engine(
        multiverse_id=multiverse_id,
        tick_index=tick_index,
        state_update_candidates=state_update_candidates,
        social_observations=social_observations,
        executed_events=executed_events,
        event_summaries=event_summaries,
    )

    apply_sociology_state_updates(sociology_result)
    persist_sociology_signals(sociology_result.signals)
    persist_sociology_prompt_influences(sociology_result.prompt_influences_for_next_tick)

    update_emotion_observability_graphs(
        emotion_self_ratings=emotion_self_ratings,
        event_summaries=event_summaries,
        god_agent_review=None,
    )

    split_candidates = generate_split_candidates(sociology_result)
    merge_candidates = generate_engine_merge_candidates(sociology_result)
    emergence_candidates = generate_emergence_candidates(sociology_result)

    provisional_tick_bundle = build_provisional_tick_bundle(
        multiverse_id=multiverse_id,
        tick_index=tick_index,
        executed_events=executed_events,
        event_summaries=event_summaries,
        sociology_result=sociology_result,
        split_candidates=split_candidates,
        merge_candidates=merge_candidates,
        emergence_candidates=emergence_candidates,
    )

    god_review = await run_god_agent_review(provisional_tick_bundle)
    tool_results = execute_god_agent_tool_calls(god_review.tool_calls)

    update_emotion_observability_graphs_with_god_review_if_needed(
        god_agent_review=god_review,
        prompt_feedback_eligible=False,
    )

    final_snapshot = persist_final_tick_snapshot(
        provisional_tick_bundle=provisional_tick_bundle,
        god_review=god_review,
        tool_results=tool_results,
    )

    publish_workspace_stream_updates(final_snapshot)
```

### 17.1 Tick Snapshot Semantics

Each tick has a provisional bundle and a final snapshot.

```text
provisional_tick_bundle:
  all tick activity before God Agent end-of-tick review

final_tick_snapshot:
  provisional bundle + God Agent review + executed God Agent tool results
```

The God Agent reviews the tick at the end of the tick, then the final tick snapshot is persisted.

---

## 18. PostgreSQL as Canonical Source of Truth

PostgreSQL stores canonical platform state and metadata.

The artifact store is used for large payloads and rendered files, but PostgreSQL remains the source of truth for object identity, state, status, versioning, and references.

### 18.1 Canonical Source by Object

| Object | Canonical source |
|---|---|
| Big Bang | PostgreSQL |
| Big Bang config | PostgreSQL row + immutable config snapshot artifact reference |
| Source-of-truth snapshot metadata | PostgreSQL |
| Source-of-truth raw files | Artifact store, referenced by PostgreSQL |
| Multiverse timeline | PostgreSQL |
| Tick status and snapshot metadata | PostgreSQL |
| Raw prompt/response payloads | Artifact store, referenced by PostgreSQL |
| Events and revisions | PostgreSQL |
| Event summaries and versions | PostgreSQL + artifact references for long bodies |
| Social posts/actions | PostgreSQL |
| Actor state | PostgreSQL |
| Graph edges and snapshots | PostgreSQL metadata; optional large graph artifact references |
| Emotion observations and snapshots | PostgreSQL |
| Sociology signals and prompt influences | PostgreSQL |
| Reports | PostgreSQL metadata + artifact store for markdown/PDF |
| Jobs | PostgreSQL |
| LLM calls | PostgreSQL metadata + artifact references |

### 18.2 Required Tables

- `big_bangs`;
- `big_bang_configs`;
- `big_bang_config_versions`;
- `source_of_truth_snapshots`;
- `actors`;
- `multiverses`;
- `multiverse_lineage_edges`;
- `tick_snapshots`;
- `tick_lineage_refs`;
- `population_archetypes`;
- `cohort_states`;
- `hero_archetypes`;
- `hero_states`;
- `events`;
- `event_revisions`;
- `event_logs`;
- `event_summaries`;
- `social_posts`;
- `oasis_actions`;
- `tool_calls`;
- `reasoning_traces`;
- `god_agent_reviews`;
- `cohort_split_candidates`;
- `cohort_splits`;
- `cohort_merge_candidates`;
- `cohort_merge_plans`;
- `cohort_merges`;
- `cohort_emergence_candidates`;
- `cohort_emergences`;
- `emotion_observations`;
- `emotion_graph_snapshots`;
- `graph_edges`;
- `graph_snapshots`;
- `sociology_signals`;
- `sociology_prompt_influences`;
- `reports`;
- `report_versions`;
- `llm_calls`;
- `jobs`;
- `artifacts`.

---

## 19. Immutability and Versioning

Historical simulation artifacts must be immutable.

Mutation means creating a new revision, version, or superseding row. Do not destructively rewrite history.

### 19.1 Versioning Rules

- event edits create `event_revision` rows;
- regenerated event summaries create new `event_summary.version` rows;
- reports are immutable by version;
- final reports may supersede earlier final reports, but old versions remain accessible;
- config changes create config versions and apply only to future ticks unless a new Big Bang is created;
- source-of-truth edits never mutate historical Big Bang snapshots;
- prompt templates should be versioned;
- LLM calls should reference prompt template version and config version.

### 19.2 Report Versioning

```text
reports
  id UUID primary key
  big_bang_id UUID
  multiverse_id UUID null
  report_type text  -- multiverse | final_big_bang
  current_version_id UUID null
  status text
  created_at timestamptz

report_versions
  id UUID primary key
  report_id UUID
  version_number int
  source_snapshot_hash text
  markdown_artifact_id UUID
  pdf_artifact_id UUID null
  generation_reason text
  supersedes_report_version_id UUID null
  status text
  created_at timestamptz
```

Completed reports cannot be edited in place. Regeneration creates a new version.

### 19.3 Summary Versioning

```text
event_summaries
  id UUID primary key
  event_id UUID
  version_number int
  source_snapshot_hash text
  summary_json jsonb
  artifact_id UUID null
  supersedes_summary_id UUID null
  status text
  created_at timestamptz
```

---

## 20. Reports

### 20.1 Per-Multiverse Report

When a multiverse terminates, run a review agent.

The report model is configurable per Big Bang. It must not be hardcoded.

Outputs:

```text
reports/multiverse/<multiverse_label>/report_v<version>.md
reports/multiverse/<multiverse_label>/report_v<version>.pdf
```

Required sections:

1. Executive Summary;
2. Timeline Overview;
3. Major Events;
4. Key Cohort Changes;
5. Social Media Dynamics;
6. Emotion Observability Trends;
7. Dependency Graph Changes;
8. Sociology Signals;
9. Branch Cause and Consequences;
10. God Agent Decisions;
11. What This Timeline Suggests;
12. Uncertainty and Failure Modes;
13. Evidence Appendix.

### 20.2 Final Big Bang Report

After all multiverses terminate, run a final condensation stage.

The final agent reads:

- every per-multiverse markdown report;
- every per-multiverse PDF if available;
- Big Bang config;
- aggregate metrics;
- branch graph;
- emotion-observability graphs;
- dependency/multiplex graphs;
- sociology signals;
- final timeline statuses.

Outputs:

```text
reports/final_big_bang_report_v<version>.md
reports/final_big_bang_report_v<version>.pdf
```

Required sections:

1. Executive Summary;
2. Scenario Recap;
3. Multiverse Map;
4. Most Common Outcomes;
5. Rare but High-Impact Outcomes;
6. Most Likely Trajectory;
7. Key Branching Drivers;
8. Important Cohort Dynamics;
9. Emotion Observability Trends;
10. Dependency and Influence Dynamics;
11. Sociology Model Findings;
12. Events That Changed the Future;
13. Recommended Interpretation;
14. Limitations;
15. Appendix.

---

## 21. Big Bang Settings

Route:

```text
/workspace/{big_bang_id}/settings
```

Settings are per Big Bang.

Sections:

1. Simulation Clock;
2. Models;
3. Report Agents;
4. God Agent;
5. Branch Policy;
6. Cohort Behavior;
7. Emotion Observability Graphs;
8. Dependency and Multiplex Graphs;
9. Sociology Presets;
10. Social Media / OASIS;
11. Storage and Artifacts;
12. Source of Truth Snapshot.

### 21.1 Model Configs

Each job type is configurable:

- initializer agent;
- cohort decision agent;
- hero decision agent;
- God Agent;
- event summary agent;
- multiverse report agent;
- final Big Bang report agent;
- PDF formatting agent.

Each model config includes:

- provider;
- model slug;
- temperature;
- max tokens;
- timeout;
- retry count;
- structured-output mode;
- fallback model;
- prompt template version;
- schema version.

OpenRouter is the default routing provider. The exact model slugs are user-configurable per Big Bang.

---

## 22. Backend Architecture

### 22.1 Primary Stack

Use Python.

Recommended stack:

```text
FastAPI
Pydantic
SQLAlchemy 2.x
PostgreSQL
Alembic
Redis
Celery or Dramatiq
WeasyPrint / Playwright / ReportLab for PDF rendering
```

### 22.2 Backend Modules

```text
backend/
  app/
    main.py
    api/
      big_bangs.py
      workspace.py
      multiverses.py
      ticks.py
      events.py
      social.py
      actors.py
      cohorts.py
      heroes.py
      graphs.py
      emotion_observability.py
      sociology.py
      reports.py
      settings.py
      jobs.py
    core/
      config.py
      clock.py
      ids.py
      labels.py
      errors.py
    db/
      models.py
      session.py
      migrations/
    source_of_truth/
      loader.py
      validator.py
      snapshotter.py
    simulation/
      initializer.py
      tick_runner.py
      branch_engine.py
      god_agent.py
      god_tools.py
      event_engine.py
      social_engine.py
      cohort_engine.py
      hero_engine.py
      emotion_observability_engine.py
      graph_engine.py
      sociology_engine.py
      report_engine.py
    llm/
      provider.py
      openrouter_provider.py
      prompt_builder.py
      schemas.py
      redaction.py
    storage/
      artifact_store.py
      run_ledger.py
      pdf_store.py
    jobs/
      queues.py
      workers.py
      tasks.py
```

### 22.3 Async Job Types

- initialize_big_bang;
- run_multiverse_tick;
- run_cohort_decisions;
- run_hero_decisions;
- execute_due_events;
- summarize_event;
- run_sociology_update;
- update_emotion_observability_graphs;
- update_graph_layers;
- run_god_review;
- execute_god_tool_call;
- create_branch;
- generate_multiverse_report;
- generate_final_big_bang_report;
- render_pdf_report.

### 22.4 Locking and Idempotency

Use PostgreSQL row-level locks or advisory locks to prevent two workers from running the same timeline tick simultaneously.

Use idempotency keys for:

- branch creation;
- event execution;
- event revision creation;
- event summary generation;
- sociology signal generation;
- emotion graph updates;
- graph snapshot generation;
- God Agent tool calls;
- report generation;
- PDF rendering.

---

## 23. API Routes

### 23.1 Big Bangs

```text
GET    /api/big-bangs
POST   /api/big-bangs
GET    /api/big-bangs/{big_bang_id}
PATCH  /api/big-bangs/{big_bang_id}
POST   /api/big-bangs/{big_bang_id}/start
POST   /api/big-bangs/{big_bang_id}/pause
POST   /api/big-bangs/{big_bang_id}/resume
GET    /api/big-bangs/{big_bang_id}/reports
POST   /api/big-bangs/{big_bang_id}/reports/final
```

### 23.2 Workspace

```text
GET /api/workspace/{big_bang_id}/state
GET /api/workspace/{big_bang_id}/activity
GET /api/workspace/{big_bang_id}/stream
```

`stream` should use WebSocket or Server-Sent Events.

### 23.3 Multiverses

```text
GET    /api/big-bangs/{big_bang_id}/multiverses
GET    /api/multiverses/{multiverse_id}
GET    /api/multiverses/{multiverse_id}/lineage
GET    /api/multiverses/{multiverse_id}/ticks
POST   /api/multiverses/{multiverse_id}/simulate-next-tick
POST   /api/multiverses/{multiverse_id}/terminate
POST   /api/multiverses/{multiverse_id}/report
```

### 23.4 Ticks

```text
GET /api/ticks/{tick_snapshot_id}
GET /api/ticks/{tick_snapshot_id}/details
GET /api/ticks/{tick_snapshot_id}/reasoning-traces
GET /api/ticks/{tick_snapshot_id}/events
GET /api/ticks/{tick_snapshot_id}/social
GET /api/ticks/{tick_snapshot_id}/tool-calls
GET /api/ticks/{tick_snapshot_id}/emotion-observability
GET /api/ticks/{tick_snapshot_id}/graph-deltas
GET /api/ticks/{tick_snapshot_id}/sociology-signals
GET /api/ticks/{tick_snapshot_id}/god-review
```

### 23.5 Actors

```text
GET /api/big-bangs/{big_bang_id}/actors
GET /api/actors/{actor_id}
GET /api/actors/{actor_id}/timeline
GET /api/actors/{actor_id}/events
GET /api/actors/{actor_id}/graphs
GET /api/actors/{actor_id}/sociology-signals
GET /api/actors/{actor_id}/emotion-observability
```

### 23.6 Graphs and Emotion Observability Graphs

```text
GET /api/big-bangs/{big_bang_id}/emotion-observability
GET /api/multiverses/{multiverse_id}/emotion-observability
GET /api/actors/{actor_id}/emotion-observability

GET /api/big-bangs/{big_bang_id}/graphs
GET /api/multiverses/{multiverse_id}/graphs
GET /api/multiverses/{multiverse_id}/graphs/{graph_layer}
GET /api/graph-edges/{edge_id}
```

### 23.7 Sociology

```text
GET /api/multiverses/{multiverse_id}/sociology-signals
GET /api/ticks/{tick_snapshot_id}/sociology-signals
GET /api/actors/{actor_id}/sociology-signals
GET /api/actors/{actor_id}/sociology-prompt-influences
```

### 23.8 God Agent

```text
GET  /api/ticks/{tick_snapshot_id}/god-review
GET  /api/god-reviews/{god_review_id}
GET  /api/god-reviews/{god_review_id}/tool-calls
POST /api/god-reviews/{god_review_id}/regenerate-summary
```

---

## 24. Artifact Storage

For each Big Bang:

```text
artifacts/
  big_bang_<id>/
    input/
    configs/
      source_of_truth/
      model_config_v<version>.json
      simulation_config_v<version>.json
    raw_llm_calls/
    sanitized_llm_calls/
    multiverses/
      M1/
        ticks/
        events/
        emotion_observability/
        graph_snapshots/
        sociology_signals/
        god_reviews/
        reports/
      M1.1/
        ticks/
        events/
        emotion_observability/
        graph_snapshots/
        sociology_signals/
        god_reviews/
        reports/
    reports/
      final_big_bang_report_v<version>.md
      final_big_bang_report_v<version>.pdf
```

PostgreSQL stores canonical metadata and artifact references. Large files may live on disk or object storage.

---

## 25. Implementation Milestones

These are delivery milestones for the full V1 simulation platform. They are not a reduction of scope into a minimal prototype.

### Milestone 1 — Personal Workspace Shell

- landing page;
- Big Bangs page;
- New Big Bang page;
- workspace shell with progressive-disclosure layout;
- center timeline graph placeholder;
- inspector pane;
- collapsible activity drawer;
- tick detail drawer.

### Milestone 2 — Database and Canonical Run Model

- PostgreSQL schema;
- actor abstraction;
- Big Bang model;
- multiverse/tick model;
- lineage references;
- artifact reference model;
- versioning tables.

### Milestone 3 — Recursive Multiverse Graph

- Big Bang root;
- horizontal timelines;
- recursive branches;
- user-facing labels;
- click timeline;
- click tick;
- open tick detail drawer;
- collapsed child branches.

### Milestone 4 — Tick Engine and Event Layer

- simulate one tick;
- agent decisions;
- event queue;
- event revisions;
- social posts;
- OASIS actions;
- logs;
- event summaries.

### Milestone 5 — Source of Truth and Modeling Layer

- source-of-truth loader/snapshotter;
- sociology engine;
- sociology prompt influences;
- graph engine;
- emotion-observability graph engine;
- UI endpoints.

### Milestone 6 — God Agent and Tool Calls

- end-of-tick God Agent review;
- God Agent tool-call execution;
- branch creation;
- split approval;
- merge planning/approval;
- cohort emergence approval;
- timeline termination/freeze.

### Milestone 7 — Reports

- per-multiverse markdown/PDF;
- report versioning;
- final Big Bang markdown/PDF;
- evidence appendix.

---

## 26. Acceptance Criteria

The full V1 simulation platform is successful when:

1. landing page has one clear Start Simulation button;
2. user can create a new Big Bang from a distinct URL;
3. each workspace displays exactly one Big Bang;
4. center pane shows recursive multiverse timelines;
5. UI uses progressive disclosure rather than exposing every technical panel at once;
6. clicking a multiverse line updates the inspector pane;
7. clicking a tick opens the tick detail drawer;
8. event summaries are generated after event execution;
9. reasoning traces stream into the inspector/detail experience as structured summaries;
10. raw artifacts are available through advanced/debug views only;
11. God Agent runs at the end of every tick;
12. God Agent authorizes recursive branches through tool calls;
13. branch/multiverse engine persists authorized branches;
14. split pipeline supports LLM/cohort/hero proposal → engine validation → God Agent approval/rejection → engine persistence;
15. merge pipeline supports engine candidate generation → God Agent tool-call planning → engine validation → God Agent approval/rejection → engine persistence;
16. God Agent can approve cohort emergence;
17. source-of-truth files are snapshotted per Big Bang;
18. sociology engine runs before emotion-observability graph updates;
19. sociology prompt influences can be inserted into future prompts;
20. emotion values are parsed, graphed, and reported but not fed into future prompts;
21. dependency/trust/exposure/influence/coalition/conflict/OASIS graph layers are persisted and inspectable;
22. sociology transitions are logged and visible in tick details;
23. multiverse reports are created when timelines terminate;
24. final Big Bang report is created after all timelines terminate;
25. PostgreSQL stores canonical platform state and metadata;
26. large/raw artifacts are referenced from PostgreSQL;
27. historical logs remain immutable;
28. regenerated summaries and reports create new versions rather than overwriting old versions.

---

## 27. FAQ

### Is this a minimal prototype?

No. This specification describes the full V1 simulation platform. It can be delivered in milestones, but the target product is the complete recursive multiverse workbench.

### Does WorldFork include single sources of truth?

Yes. Source-of-truth files are mandatory for emotions, behavior axes, ideology axes, expression scales, event types, social action types, graph edge types, sociology models, tool registry, and report templates. Every Big Bang snapshots them.

### Does WorldFork include emotion graphs?

Yes. Emotion-observability graphs are required. They use explicit `0–10` values from structured prompt outputs and summary agents.

### Are emotion values fed into future prompts?

No. Emotion values are parsed, stored, graphed, and reported, but they are not fed into future prompts and are not canonical actor state.

### How does sociology influence future agent behavior?

The sociology engine produces explicit `sociology_prompt_influences`, such as perceived majority pressure, silence pressure, mobilization threshold status, attention salience, identity salience, and exposure/trust context. These can be inserted into future prompts as explicit, inspectable simulation context.

### Does WorldFork use hidden emotional model-state controls?

No. The platform only uses explicit state, source-of-truth definitions, structured prompt context, and observable outputs. There is no hidden activation/model-state steering.

### Does WorldFork include dependency graphs?

Yes. Dependency graphs are required, alongside exposure, trust, influence, coalition, conflict, and OASIS/social-media interaction graphs.

### Does WorldFork include sociology theories?

Yes. The sociology engine includes bounded confidence / anchored opinion drift, Granovetter thresholds, spiral of silence, homophily, complex contagion, social identity salience, and attention decay / agenda setting.

### Can one timeline branch many times?

Yes. Branching is recursive. Any child timeline can branch again.

### Are old ticks copied when a branch happens?

No. Old tick snapshots are referenced immutably. The UI materializes inherited ticks under the child timeline label.

### Who can authorize a branch?

Only the God Agent can authorize a branch.

### Who persists the branch?

The branch/multiverse engine persists branch creation after validating the God Agent’s tool call.

### Can the God Agent create new cohorts?

The God Agent can approve new cohort emergence every tick. Cohorts/heroes or the sociology engine may propose emergence, but the engine validates and the God Agent approves or rejects it.

### Can cohorts propose merges?

No. Merges are proposed by the deterministic engine, reviewed by the God Agent, and persisted only after validation and approval.

### What happens when all timelines end?

Each terminated multiverse gets a report. When all timelines terminate, a final Big Bang condensation report is generated.

---

## 28. GitHub Issue / PR Description

### Title

Build WorldFork as a full V1 recursive-multiverse simulation platform

### Summary

Build WorldFork as a personal recursive simulation workbench centered around one Big Bang workspace. The workspace must show recursive multiverse timelines where every child timeline can branch again. The platform must include the full modeling substrate: source-of-truth taxonomies, actor abstraction, emotion-observability graphs, dependency/multiplex graphs, sociology models, God Agent tool-call authority, hero archetypes, cohort split/merge/emergence workflows, immutable versioning, PostgreSQL canonical state, and report generation.

### Required Changes

- Create minimal landing page with Start Simulation button.
- Create Big Bangs page and New Big Bang page.
- Build workspace route `/workspace/{big_bang_id}`.
- Implement progressive-disclosure workspace UI.
- Add recursive multiverse timeline graph.
- Add contextual inspector pane.
- Add collapsible activity drawer.
- Add bottom tick-detail drawer.
- Implement PostgreSQL schema for Big Bangs, actors, multiverses, ticks, lineage refs, cohorts, heroes, events, event revisions, social posts, tool calls, reasoning traces, reports, emotion observations, graph edges, sociology signals, and God Agent reviews.
- Implement source-of-truth snapshots for emotions, behaviors, ideology axes, expression levels, event types, social actions, graph layers, and sociology presets.
- Implement prompt-driven emotion-observability graphs that are not fed back into future prompts.
- Implement dependency/exposure/trust/influence/coalition/conflict/OASIS graph layers.
- Implement sociology layer updates and sociology prompt influences.
- Implement God Agent end-of-tick review.
- Implement God Agent structured tool calls for branching, split approval, merge planning/approval, emergence approval, freezing, termination, and report readiness.
- Implement event summary generation after successful event execution.
- Implement immutable versioning for events, summaries, reports, configs, and artifacts.
- Implement per-multiverse and final Big Bang report generation.

### Done When

- User can create a Big Bang.
- User can watch recursive multiverse branches form.
- User can click a timeline, tick, event, actor, graph change, or sociology signal and inspect details.
- UI starts simple and progressively reveals advanced panels.
- Emotion-observability graphs, dependency graphs, and sociology updates are visible in review.
- Emotion values are not fed into future prompts.
- Sociology prompt influences are inserted into future prompts as explicit simulation context.
- God Agent runs at the end of each tick and uses structured tool calls.
- PostgreSQL is the canonical source of platform state.
- Reports are generated at multiverse and Big Bang levels.
- Historical artifacts are immutable and auditable.
