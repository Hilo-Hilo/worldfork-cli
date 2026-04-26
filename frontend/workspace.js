(function () {
  'use strict';

  const DEFAULT_OPTIONS = {
    apiBase: '/api/frontend/workspace',
    maxActivityItems: 80,
    maxSignalItems: 8,
  };

  const STATUS_TONE = {
    running: 'live',
    active: 'live',
    completed: 'done',
    complete: 'done',
    terminated: 'done',
    frozen: 'hold',
    freeze: 'hold',
    failed: 'bad',
    error: 'bad',
    branched: 'branch',
  };

  function fetchWorkspace(bigBangId, options) {
    const settings = Object.assign({}, DEFAULT_OPTIONS, options || {});
    const id = encodeURIComponent(requireValue(bigBangId, 'bigBangId'));
    const endpoint = `${settings.apiBase}/${id}`;

    return fetch(endpoint, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: settings.signal,
      credentials: settings.credentials || 'same-origin',
    }).then((response) => {
      if (!response.ok) {
        const error = new Error(`Workspace request failed with HTTP ${response.status}`);
        error.status = response.status;
        error.endpoint = endpoint;
        throw error;
      }
      return response.json();
    });
  }

  function mountWorkspace(root, input, options) {
    const target = resolveRoot(root);
    const settings = Object.assign({}, DEFAULT_OPTIONS, options || {});
    const state = {
      bigBangId: typeof input === 'string' ? input : input && input.big_bang_id,
      payload: typeof input === 'object' && input ? input.payload || input.workspace || input : null,
      normalized: null,
      selection: { timelineId: null, tickId: null },
    };

    target.classList.add('wf-workspace-host');

    if (state.payload) {
      state.normalized = normalizeWorkspacePayload(state.payload);
      renderWorkspace(target, state, settings);
      return Promise.resolve(apiFor(target, state, settings));
    }

    renderLoading(target);
    return fetchWorkspace(state.bigBangId, settings)
      .then((payload) => {
        state.payload = payload;
        state.normalized = normalizeWorkspacePayload(payload);
        renderWorkspace(target, state, settings);
        return apiFor(target, state, settings);
      })
      .catch((error) => {
        renderError(target, error);
        throw error;
      });
  }

  function renderWorkspaceVisualization(root, payload, options) {
    const target = resolveRoot(root);
    const state = {
      payload,
      normalized: normalizeWorkspacePayload(payload),
      selection: { timelineId: null, tickId: null },
    };
    target.classList.add('wf-workspace-host');
    renderWorkspace(target, state, Object.assign({}, DEFAULT_OPTIONS, options || {}));
    return apiFor(target, state, Object.assign({}, DEFAULT_OPTIONS, options || {}));
  }

  function normalizeWorkspacePayload(payload) {
    const source = payload || {};
    const bigBang = source.big_bang || source.bigBang || source.bigbang || source;
    const rawTimelines = firstArray(
      source.timelines,
      source.multiverse_timelines,
      source.multiverses,
      source.workspace && source.workspace.timelines,
      bigBang.timelines,
    );
    const reports = firstArray(source.reports, source.multiverse_reports, bigBang.reports);

    const timelines = rawTimelines.map((timeline, index) => normalizeTimeline(timeline, index));
    const byTimelineId = new Map(timelines.map((timeline) => [timeline.id, timeline]));
    const activity = buildActivity(source, timelines);
    const signals = normalizeSignals(source, timelines);

    return {
      id: pickString(bigBang.id, bigBang.big_bang_id, source.big_bang_id, source.id),
      label: pickString(bigBang.ui_label, bigBang.label, bigBang.name, source.ui_big_bang_label, source.name, 'Big Bang'),
      scenario: pickString(bigBang.scenario, bigBang.scenario_input, source.scenario, source.scenario_input, ''),
      status: pickString(bigBang.status, source.status, ''),
      tickDuration: pickString(bigBang.tick_duration, source.tick_duration, source.simulation_config && source.simulation_config.tick_duration, ''),
      currentTick: pickNumber(bigBang.current_tick_index, source.current_tick_index, source.current_tick),
      timelines,
      byTimelineId,
      activity,
      signals,
      reports,
      raw: source,
    };
  }

  function normalizeTimeline(timeline, index) {
    const rawTicks = firstArray(timeline.ticks, timeline.tick_snapshots, timeline.timeline_ticks, timeline.snapshots);
    const id = pickString(timeline.canonical_multiverse_id, timeline.multiverse_id, timeline.id, timeline.uuid, `timeline-${index + 1}`);
    const label = pickString(timeline.ui_multiverse_label, timeline.ui_label, timeline.label, timeline.name, `M${index + 1}`);
    const parentId = pickString(timeline.parent_multiverse_id, timeline.parent_timeline_id, timeline.parent_id, '');
    const branchFromTick = pickString(timeline.branch_from_tick_label, timeline.branch_from_ui_tick_label, timeline.branch_from_tick, '');

    const ticks = rawTicks.map((tick, tickIndex) => normalizeTick(tick, tickIndex, id, label));
    const tickById = new Map(ticks.map((tick) => [tick.id, tick]));

    return {
      id,
      label,
      parentId,
      branchFromTick,
      depth: pickNumber(timeline.depth, timeline.lineage_depth, label.split('.').length - 1, 0),
      status: pickString(timeline.status, timeline.lifecycle_state, ''),
      summary: pickString(timeline.summary, timeline.latest_summary, timeline.description, ''),
      ticks,
      tickById,
      raw: timeline,
    };
  }

  function normalizeTick(tick, index, timelineId, timelineLabel) {
    const id = pickString(tick.canonical_tick_snapshot_id, tick.tick_snapshot_id, tick.tick_id, tick.id, `${timelineId}:tick-${index}`);
    const label = pickString(tick.ui_tick_label, tick.label, tick.tick_label, `${timelineLabel}:T${pickNumber(tick.tick_index, tick.index, index)}`);
    const events = firstArray(tick.events, tick.event_logs, tick.event_summaries, tick.event_summary ? [tick.event_summary] : null);
    const social = firstArray(tick.social_media_logs, tick.social_actions, tick.oasis_actions, tick.oasis_action_logs);
    const graph = firstArray(tick.graph_deltas, tick.social_graph_deltas, tick.graph_changes);
    const sociology = firstArray(tick.sociology_signals, tick.signals, tick.sociology);
    const emotions = firstArray(tick.emotion_observations, tick.emotion_graphs, tick.emotion_graph_snapshots, tick.emotions);
    const reviews = firstArray(tick.god_agent_reviews, tick.god_agent_review ? [tick.god_agent_review] : null, tick.reviews);
    const branches = firstArray(tick.branch_decisions, tick.branches, tick.child_timelines);

    return {
      id,
      label,
      index: pickNumber(tick.tick_index, tick.index, index),
      elapsed: pickString(tick.elapsed_since_big_bang, tick.elapsed, tick.human_time, ''),
      status: pickString(tick.status, tick.lifecycle_state, branchStatus(branches), ''),
      summary: pickString(tick.summary, tick.tick_summary, tick.event_summary && tick.event_summary.summary, ''),
      events,
      social,
      graph,
      sociology,
      emotions,
      reviews,
      branches,
      raw: tick,
    };
  }

  function renderWorkspace(root, state, options) {
    const data = state.normalized;
    state.selection.timelineId = state.selection.timelineId || (data.timelines[0] && data.timelines[0].id);
    state.selection.tickId = state.selection.tickId || firstTickId(data.byTimelineId.get(state.selection.timelineId));

    root.innerHTML = '';
    const shell = el('section', 'wf-workspace', { 'data-status': tone(data.status) });
    shell.appendChild(renderHeader(data));

    const body = el('div', 'wf-workspace__grid');
    body.appendChild(renderTimelinePanel(data, state));
    body.appendChild(renderInspectorPanel(data, state));
    body.appendChild(renderSidePanel(data, state, options));
    shell.appendChild(body);

    shell.addEventListener('click', (event) => handleWorkspaceClick(event, root, state, options));
    root.appendChild(shell);
  }

  function renderHeader(data) {
    const header = el('header', 'wf-workspace__header');
    const copy = el('div', 'wf-workspace__title-block');
    copy.appendChild(el('p', 'wf-eyebrow', {}, 'Recursive simulation workspace'));
    copy.appendChild(el('h1', 'wf-workspace__title', {}, data.label));
    if (data.scenario) copy.appendChild(el('p', 'wf-workspace__scenario', {}, data.scenario));

    const metrics = el('div', 'wf-workspace__metrics');
    metrics.appendChild(metric('Timelines', data.timelines.length));
    metrics.appendChild(metric('Ticks', data.timelines.reduce((total, timeline) => total + timeline.ticks.length, 0)));
    metrics.appendChild(metric('Tick duration', data.tickDuration || 'unknown'));
    if (data.status) metrics.appendChild(metric('Status', data.status));

    header.appendChild(copy);
    header.appendChild(metrics);
    return header;
  }

  function renderTimelinePanel(data, state) {
    const panel = el('section', 'wf-panel wf-timeline-panel');
    panel.appendChild(panelHead('Multiverse timelines', 'Click a line or tick to inspect real simulation state.'));

    if (!data.timelines.length) {
      panel.appendChild(emptyState('No timelines returned by the workspace API yet.'));
      return panel;
    }

    const rows = el('div', 'wf-timeline-map');
    data.timelines.forEach((timeline) => {
      const selected = timeline.id === state.selection.timelineId;
      const row = el('article', `wf-timeline-row${selected ? ' is-selected' : ''}`, {
        'data-wf-timeline-id': timeline.id,
        style: `--wf-depth:${Math.max(0, timeline.depth || 0)}`,
      });

      const label = el('button', 'wf-timeline-label', { type: 'button', 'data-wf-timeline-id': timeline.id });
      label.appendChild(el('span', 'wf-timeline-label__name', {}, timeline.label));
      label.appendChild(el('span', `wf-status-pill is-${tone(timeline.status)}`, {}, timeline.status || 'unknown'));
      if (timeline.branchFromTick) label.appendChild(el('span', 'wf-branch-origin', {}, `from ${timeline.branchFromTick}`));
      row.appendChild(label);

      const track = el('div', 'wf-tick-track');
      if (!timeline.ticks.length) {
        track.appendChild(el('span', 'wf-muted', {}, 'No ticks'));
      }
      timeline.ticks.forEach((tick) => {
        const isTickSelected = selected && tick.id === state.selection.tickId;
        const chip = el('button', `wf-tick-chip is-${tone(tick.status)}${isTickSelected ? ' is-selected' : ''}`, {
          type: 'button',
          title: tick.elapsed || tick.summary || tick.label,
          'data-wf-timeline-id': timeline.id,
          'data-wf-tick-id': tick.id,
        });
        chip.appendChild(el('span', 'wf-tick-chip__label', {}, tickShortLabel(tick.label)));
        chip.appendChild(el('span', 'wf-tick-chip__count', {}, String(tick.events.length + tick.social.length + tick.graph.length + tick.sociology.length)));
        track.appendChild(chip);
      });
      row.appendChild(track);
      rows.appendChild(row);
    });

    panel.appendChild(rows);
    return panel;
  }

  function renderInspectorPanel(data, state) {
    const timeline = data.byTimelineId.get(state.selection.timelineId) || data.timelines[0];
    const tick = timeline && (timeline.tickById.get(state.selection.tickId) || timeline.ticks[0]);
    const panel = el('section', 'wf-panel wf-inspector-panel');
    panel.appendChild(panelHead('Inspector', 'Summary helpers for the selected timeline and tick.'));

    if (!timeline) {
      panel.appendChild(emptyState('Select a timeline after the API returns simulation data.'));
      return panel;
    }

    const hero = el('div', 'wf-inspector-hero');
    hero.appendChild(el('div', 'wf-inspector-hero__label', {}, timeline.label));
    hero.appendChild(el('div', `wf-status-pill is-${tone(timeline.status)}`, {}, timeline.status || 'unknown'));
    if (timeline.summary) hero.appendChild(el('p', 'wf-inspector-hero__summary', {}, timeline.summary));
    panel.appendChild(hero);

    if (!tick) {
      panel.appendChild(emptyState('This timeline has no tick snapshots yet.'));
      return panel;
    }

    panel.appendChild(renderTickSummary(tick));
    panel.appendChild(renderSignalPanels(tick));
    return panel;
  }

  function renderTickSummary(tick) {
    const wrap = el('section', 'wf-tick-summary');
    const heading = el('div', 'wf-section-heading');
    heading.appendChild(el('h3', '', {}, tick.label));
    if (tick.elapsed) heading.appendChild(el('span', 'wf-muted', {}, tick.elapsed));
    wrap.appendChild(heading);
    if (tick.summary) wrap.appendChild(el('p', 'wf-tick-summary__copy', {}, tick.summary));

    const stats = el('div', 'wf-summary-grid');
    stats.appendChild(metric('Events', tick.events.length));
    stats.appendChild(metric('Social/OASIS', tick.social.length));
    stats.appendChild(metric('Graph deltas', tick.graph.length));
    stats.appendChild(metric('Sociology', tick.sociology.length));
    stats.appendChild(metric('Emotion obs', tick.emotions.length));
    stats.appendChild(metric('God reviews', tick.reviews.length));
    wrap.appendChild(stats);
    return wrap;
  }

  function renderSignalPanels(tick) {
    const grid = el('div', 'wf-signal-grid');
    grid.appendChild(signalPanel('Events', tick.events, describeEvent));
    grid.appendChild(signalPanel('Social / OASIS', tick.social, describeAction));
    grid.appendChild(signalPanel('Graph changes', tick.graph, describeGraph));
    grid.appendChild(signalPanel('Sociology signals', tick.sociology, describeSignal));
    grid.appendChild(signalPanel('Emotion observations', tick.emotions, describeEmotion));
    grid.appendChild(signalPanel('God Agent review', tick.reviews, describeReview));
    return grid;
  }

  function renderSidePanel(data, state, options) {
    const panel = el('aside', 'wf-panel wf-side-panel');
    panel.appendChild(panelHead('Activity rail', 'Chronological API-backed simulation changes.'));

    const activity = data.activity.slice(0, options.maxActivityItems);
    if (!activity.length) {
      panel.appendChild(emptyState('No activity records were returned.'));
    } else {
      const rail = el('ol', 'wf-activity-rail');
      activity.forEach((item) => {
        const li = el('li', 'wf-activity-item');
        li.appendChild(el('span', `wf-activity-dot is-${tone(item.kind)}`));
        const body = el('div', 'wf-activity-item__body');
        body.appendChild(el('strong', '', {}, item.label));
        body.appendChild(el('p', '', {}, item.summary));
        if (item.context) body.appendChild(el('span', 'wf-muted', {}, item.context));
        li.appendChild(body);
        rail.appendChild(li);
      });
      panel.appendChild(rail);
    }

    panel.appendChild(renderWorkspaceSignals(data));
    return panel;
  }

  function renderWorkspaceSignals(data) {
    const wrap = el('section', 'wf-workspace-signals');
    wrap.appendChild(el('h3', '', {}, 'Workspace signals'));
    if (!data.signals.length) {
      wrap.appendChild(emptyState('No aggregate signal payloads found.'));
      return wrap;
    }
    const list = el('div', 'wf-aggregate-signals');
    data.signals.forEach((signal) => {
      const card = el('article', 'wf-aggregate-signal');
      card.appendChild(el('span', 'wf-aggregate-signal__kind', {}, signal.kind));
      card.appendChild(el('strong', '', {}, signal.label));
      if (signal.value !== '') card.appendChild(el('span', 'wf-aggregate-signal__value', {}, signal.value));
      list.appendChild(card);
    });
    wrap.appendChild(list);
    return wrap;
  }

  function signalPanel(title, items, describe) {
    const card = el('section', 'wf-signal-card');
    card.appendChild(el('h3', '', {}, title));
    if (!items.length) {
      card.appendChild(el('p', 'wf-empty-inline', {}, 'None returned for this tick.'));
      return card;
    }
    const list = el('ul', 'wf-signal-list');
    items.slice(0, DEFAULT_OPTIONS.maxSignalItems).forEach((item) => {
      const row = describe(item);
      const li = el('li', 'wf-signal-list__item');
      li.appendChild(el('strong', '', {}, row.title));
      if (row.meta) li.appendChild(el('span', 'wf-muted', {}, row.meta));
      if (row.body) li.appendChild(el('p', '', {}, row.body));
      list.appendChild(li);
    });
    if (items.length > DEFAULT_OPTIONS.maxSignalItems) {
      card.appendChild(el('p', 'wf-muted', {}, `${items.length - DEFAULT_OPTIONS.maxSignalItems} more in raw payload`));
    }
    card.appendChild(list);
    return card;
  }

  function summarizeSelection(payload, timelineId, tickId) {
    const data = payload.timelines ? payload : normalizeWorkspacePayload(payload);
    const timeline = data.byTimelineId.get(timelineId) || data.timelines[0] || null;
    const tick = timeline && (timeline.tickById.get(tickId) || timeline.ticks[0] || null);
    return {
      bigBang: { id: data.id, label: data.label, status: data.status },
      timeline: timeline && { id: timeline.id, label: timeline.label, status: timeline.status, tickCount: timeline.ticks.length },
      tick: tick && {
        id: tick.id,
        label: tick.label,
        status: tick.status,
        summary: tick.summary,
        counts: {
          events: tick.events.length,
          social: tick.social.length,
          graph: tick.graph.length,
          sociology: tick.sociology.length,
          emotions: tick.emotions.length,
          reviews: tick.reviews.length,
        },
      },
    };
  }

  function handleWorkspaceClick(event, root, state, options) {
    const tickButton = event.target.closest('[data-wf-tick-id]');
    if (tickButton) {
      state.selection.timelineId = tickButton.getAttribute('data-wf-timeline-id');
      state.selection.tickId = tickButton.getAttribute('data-wf-tick-id');
      renderWorkspace(root, state, options);
      return;
    }

    const timelineButton = event.target.closest('[data-wf-timeline-id]');
    if (timelineButton) {
      const id = timelineButton.getAttribute('data-wf-timeline-id');
      const timeline = state.normalized.byTimelineId.get(id);
      state.selection.timelineId = id;
      state.selection.tickId = firstTickId(timeline) || null;
      renderWorkspace(root, state, options);
    }
  }

  function buildActivity(source, timelines) {
    const explicit = firstArray(source.activity, source.activity_rail, source.audit_log, source.timeline_activity);
    if (explicit.length) {
      return explicit.map((item) => ({
        kind: pickString(item.kind, item.type, item.event_type, 'activity'),
        label: pickString(item.label, item.title, item.ui_tick_label, 'Activity'),
        summary: pickString(item.summary, item.description, item.message, compactJson(item)),
        context: pickString(item.context, item.timestamp, item.created_at, ''),
      }));
    }

    const items = [];
    timelines.forEach((timeline) => {
      timeline.ticks.forEach((tick) => {
        pushActivity(items, 'event', tick.events, timeline, tick, describeEvent);
        pushActivity(items, 'social', tick.social, timeline, tick, describeAction);
        pushActivity(items, 'graph', tick.graph, timeline, tick, describeGraph);
        pushActivity(items, 'signal', tick.sociology, timeline, tick, describeSignal);
        pushActivity(items, 'emotion', tick.emotions, timeline, tick, describeEmotion);
        pushActivity(items, 'review', tick.reviews, timeline, tick, describeReview);
      });
    });
    return items;
  }

  function pushActivity(items, kind, records, timeline, tick, describe) {
    records.forEach((record) => {
      const summary = describe(record);
      items.push({ kind, label: summary.title, summary: summary.body || summary.meta || 'Recorded change', context: `${timeline.label} · ${tick.label}` });
    });
  }

  function normalizeSignals(source, timelines) {
    const explicit = firstArray(source.signals, source.aggregate_signals, source.workspace_signals);
    if (explicit.length) {
      return explicit.map((signal) => ({
        kind: pickString(signal.kind, signal.type, signal.model, 'signal'),
        label: pickString(signal.label, signal.name, signal.metric, 'Signal'),
        value: pickString(signal.value, signal.score, signal.level, ''),
      }));
    }

    return [
      { kind: 'coverage', label: 'Timelines with ticks', value: `${timelines.filter((timeline) => timeline.ticks.length).length}/${timelines.length}` },
      { kind: 'branching', label: 'Branching ticks', value: String(timelines.reduce((total, timeline) => total + timeline.ticks.filter((tick) => tick.branches.length).length, 0)) },
      { kind: 'reviews', label: 'God Agent reviews', value: String(timelines.reduce((total, timeline) => total + timeline.ticks.reduce((sum, tick) => sum + tick.reviews.length, 0), 0)) },
    ];
  }

  function describeEvent(item) {
    return describeGeneric(item, ['event_type', 'type', 'title', 'label'], ['summary', 'description', 'narrative', 'body'], ['actor_label', 'cohort_label', 'source']);
  }

  function describeAction(item) {
    return describeGeneric(item, ['action_type', 'platform', 'type', 'title'], ['content', 'summary', 'description', 'body'], ['actor_label', 'channel', 'surface']);
  }

  function describeGraph(item) {
    return describeGeneric(item, ['edge_type', 'layer', 'type', 'label'], ['summary', 'description', 'delta', 'change'], ['source_label', 'target_label', 'weight_delta']);
  }

  function describeSignal(item) {
    return describeGeneric(item, ['model', 'signal_type', 'type', 'label'], ['summary', 'interpretation', 'description', 'value'], ['score', 'level', 'cohort_label']);
  }

  function describeEmotion(item) {
    return describeGeneric(item, ['emotion', 'emotion_name', 'axis', 'label'], ['summary', 'interpretation', 'description', 'value'], ['actor_label', 'cohort_label', 'intensity']);
  }

  function describeReview(item) {
    return describeGeneric(item, ['decision', 'status', 'review_type', 'label'], ['summary', 'rationale', 'reasoning', 'description'], ['authorized_branch_count', 'termination_reason']);
  }

  function describeGeneric(item, titleKeys, bodyKeys, metaKeys) {
    const title = pickFromKeys(item, titleKeys) || 'Recorded item';
    const body = pickFromKeys(item, bodyKeys) || compactJson(item);
    const meta = metaKeys.map((key) => item && item[key]).filter((value) => value !== undefined && value !== null && value !== '').join(' · ');
    return { title: String(title), body: String(body || ''), meta };
  }

  function pickFromKeys(item, keys) {
    if (!item || typeof item !== 'object') return item;
    for (const key of keys) {
      if (item[key] !== undefined && item[key] !== null && item[key] !== '') return item[key];
    }
    return '';
  }

  function apiFor(root, state, options) {
    return {
      root,
      get payload() { return state.payload; },
      get normalized() { return state.normalized; },
      get selection() { return Object.assign({}, state.selection); },
      select(timelineId, tickId) {
        state.selection.timelineId = timelineId;
        state.selection.tickId = tickId || firstTickId(state.normalized.byTimelineId.get(timelineId));
        renderWorkspace(root, state, options);
        return summarizeSelection(state.normalized, state.selection.timelineId, state.selection.tickId);
      },
      summarizeSelection(timelineId, tickId) {
        return summarizeSelection(state.normalized, timelineId || state.selection.timelineId, tickId || state.selection.tickId);
      },
    };
  }

  function renderLoading(root) {
    root.innerHTML = '';
    root.classList.add('wf-workspace-host');
    root.appendChild(el('section', 'wf-workspace wf-workspace--loading', {}, 'Loading workspace visualization...'));
  }

  function renderError(root, error) {
    root.innerHTML = '';
    root.classList.add('wf-workspace-host');
    const card = el('section', 'wf-workspace wf-workspace--error');
    card.appendChild(el('h2', '', {}, 'Workspace data unavailable'));
    card.appendChild(el('p', '', {}, error && error.message ? error.message : 'The workspace API request failed.'));
    root.appendChild(card);
  }

  function panelHead(title, subtitle) {
    const head = el('div', 'wf-panel__head');
    head.appendChild(el('h2', '', {}, title));
    head.appendChild(el('p', '', {}, subtitle));
    return head;
  }

  function metric(label, value) {
    const node = el('div', 'wf-metric');
    node.appendChild(el('span', 'wf-metric__label', {}, label));
    node.appendChild(el('strong', 'wf-metric__value', {}, String(value === undefined || value === null || value === '' ? 'none' : value)));
    return node;
  }

  function emptyState(text) {
    return el('div', 'wf-empty-state', {}, text);
  }

  function el(tag, className, attrs, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    Object.entries(attrs || {}).forEach(([key, value]) => {
      if (value === undefined || value === null || value === false) return;
      node.setAttribute(key, String(value));
    });
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function requireValue(value, name) {
    if (value === undefined || value === null || value === '') throw new Error(`${name} is required`);
    return value;
  }

  function resolveRoot(root) {
    if (typeof root === 'string') {
      const node = document.querySelector(root);
      if (!node) throw new Error(`Workspace root not found: ${root}`);
      return node;
    }
    if (!root || !root.appendChild) throw new Error('A DOM root element is required');
    return root;
  }

  function firstArray() {
    for (let index = 0; index < arguments.length; index += 1) {
      const value = arguments[index];
      if (Array.isArray(value)) return value;
    }
    return [];
  }

  function pickString() {
    for (let index = 0; index < arguments.length; index += 1) {
      const value = arguments[index];
      if (value !== undefined && value !== null && value !== '') return String(value);
    }
    return '';
  }

  function pickNumber() {
    for (let index = 0; index < arguments.length; index += 1) {
      const value = arguments[index];
      if (value !== undefined && value !== null && value !== '' && Number.isFinite(Number(value))) return Number(value);
    }
    return 0;
  }

  function branchStatus(branches) {
    return branches && branches.length ? 'branched' : '';
  }

  function firstTickId(timeline) {
    return timeline && timeline.ticks[0] ? timeline.ticks[0].id : null;
  }

  function tone(value) {
    const key = String(value || '').toLowerCase();
    return STATUS_TONE[key] || key || 'neutral';
  }

  function tickShortLabel(label) {
    const text = String(label || 'T?');
    const parts = text.split(':');
    return parts[parts.length - 1] || text;
  }

  function compactJson(value) {
    if (value === undefined || value === null) return '';
    if (typeof value !== 'object') return String(value);
    try {
      return JSON.stringify(value).slice(0, 180);
    } catch (error) {
      return 'Structured payload';
    }
  }

  window.WorldForkWorkspace = {
    fetchWorkspace,
    mountWorkspace,
    normalizeWorkspacePayload,
    renderWorkspaceVisualization,
    summarizeSelection,
  };
})();
