import { useEffect, useMemo, useState } from 'react';
import type { ChangeEvent, CSSProperties, FormEvent, ReactNode } from 'react';
import { Api } from './api';
import type { BigBang, BigBangCreatePayload, BootstrapPayload, Multiverse, ScenarioBankItem, TickSnapshot, View, WorkspacePayload } from './types';
import { compactId, firstWords, fmtDate, plural, scenarioText, statusClass } from './utils';
import './styles.css';

const VIEWS: View[] = ['landing', 'big-bangs', 'setup', 'workspace', 'reports', 'report-view', 'settings', 'jobs'];
const TICK_DURATION_OPTIONS = ['1 day', '3 days', '1 week', '2 weeks', '1 month'];

type InspectorState = { type: string; payload: any } | null;
type ReportRouteRef = { kind: 'report' | 'version'; id: string } | null;
type IconName = keyof typeof ICON_PATHS;
type ActivityFilter = 'all' | 'tick' | 'tool_call' | 'job' | 'report';
type TickDetailTab = 'overview' | 'events' | 'social' | 'tools' | 'emotion' | 'graphs' | 'raw';

const ICON_PATHS = {
  menu: 'M3 6h18M3 12h18M3 18h18',
  search: 'M11 19a8 8 0 1 1 5.3-14M21 21l-4.3-4.3',
  play: 'M6 4l14 8-14 8V4z',
  pause: 'M6 4h4v16H6zM14 4h4v16h-4z',
  forward: 'M5 4l8 8-8 8M13 4l8 8-8 8',
  chart: 'M4 20V8M10 20V4M16 20v-8M22 20H2',
  settings: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM19.4 15a7.5 7.5 0 0 0 0-6l2-1.7-2-3.5-2.4 1A7.5 7.5 0 0 0 13.5 3l-.4-2.5h-4l-.4 2.5a7.5 7.5 0 0 0-3.5 1.8l-2.4-1-2 3.5 2 1.7a7.5 7.5 0 0 0 0 6l-2 1.7 2 3.5 2.4-1A7.5 7.5 0 0 0 8.5 21l.4 2.5h4l.4-2.5a7.5 7.5 0 0 0 3.5-1.8l2.4 1 2-3.5z',
  plus: 'M12 5v14M5 12h14',
  clock: 'M12 7v5l3 2M12 22a10 10 0 1 1 0-20 10 10 0 0 1 0 20z',
  grid: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
  list: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',
  chevron: 'M6 9l6 6 6-6',
  chevronUp: 'M6 15l6-6 6 6',
  chevronRight: 'M9 6l6 6-6 6',
  more: 'M5 12h.01M12 12h.01M19 12h.01',
  archive: 'M3 7h18M5 7v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7M9 11h6',
  copy: 'M9 9h11v11H9zM5 15V5h10',
  open: 'M14 3h7v7M10 14L21 3M5 5h6v0M5 5v14a2 2 0 0 0 2 2h12',
  users: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM22 21v-2a4 4 0 0 0-3-3.9M16 3.1A4 4 0 0 1 16 11',
  shield: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
  megaphone: 'M3 11l11-5v12L3 13zM14 6l5-2v16l-5-2M19 8a4 4 0 0 1 0 8',
  file: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6',
  upload: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12',
  sparkle: 'M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8',
  info: 'M12 16v-4M12 8h.01M12 22a10 10 0 1 1 0-20 10 10 0 0 1 0 20z',
  refresh: 'M3 12a9 9 0 0 1 15-6.7L21 8M21 3v5h-5M21 12a9 9 0 0 1-15 6.7L3 16M3 21v-5h5',
  eye: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
  bot: 'M12 2v4M9 12h.01M15 12h.01M5 8h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2zM2 14h2M20 14h2',
  branch: 'M6 3v6a3 3 0 0 0 3 3h6a3 3 0 0 1 3 3v6M6 3l-3 3M6 3l3 3M18 21l3-3M18 21l-3-3',
  lock: 'M5 11h14v10H5zM7 11V7a5 5 0 0 1 10 0v4',
  arrowRight: 'M5 12h14M13 5l7 7-7 7',
  activity: 'M22 12h-4l-3 9-6-18-3 9H2',
  layers: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5',
  target: 'M12 22a10 10 0 1 1 0-20 10 10 0 0 1 0 20zM12 18a6 6 0 1 1 0-12 6 6 0 0 1 0 12zM12 14a2 2 0 1 1 0-4 2 2 0 0 1 0 4z',
  sociology: 'M17 18a5 5 0 0 0-10 0M12 14a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM3 22h18',
  close: 'M18 6L6 18M6 6l12 12',
  fit: 'M9 4H4v5M20 9V4h-5M4 15v5h5M15 20h5v-5',
  minus: 'M5 12h14',
};

export default function App() {
  const [view, setView] = useState<View>(hashView());
  const [bootstrap, setBootstrap] = useState<BootstrapPayload | null>(null);
  const [bigBangs, setBigBangs] = useState<BigBang[]>([]);
  const [bigBangError, setBigBangError] = useState<string | null>(null);
  const [selectedBigBangId, setSelectedBigBangIdState] = useState<string | null>(() => initialBigBangId());
  const [workspace, setWorkspace] = useState<WorkspacePayload | null>(null);
  const [selectedMultiverseId, setSelectedMultiverseId] = useState<string | null>(null);
  const [selectedTickId, setSelectedTickId] = useState<string | null>(null);
  const [inspector, setInspector] = useState<InspectorState>(null);
  const [reportRouteRef, setReportRouteRef] = useState<ReportRouteRef>(() => initialReportRouteRef());
  const [toast, setToast] = useState('');
  const [busy, setBusy] = useState(false);
  const [navOpen, setNavOpen] = useState(false);

  function notify(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(''), 3600);
  }
  function setSelectedBigBangId(id: string | null) {
    setSelectedBigBangIdState(id);
    if (id) localStorage.setItem('worldfork:selectedBigBangId', id);
    else localStorage.removeItem('worldfork:selectedBigBangId');
  }
  function navigate(next: View) {
    window.scrollTo({ top: 0, left: 0 });
    setNavOpen(false);
    if (next !== 'report-view') setReportRouteRef(null);
    setView(next);
    window.history.pushState(null, '', routeForView(next, selectedBigBangId, reportRouteRef));
    if (!['workspace', 'reports'].includes(next)) setWorkspace(null);
  }
  function openReportView(kind: 'report' | 'version', id: string) {
    const next = { kind, id };
    setReportRouteRef(next);
    setView('report-view');
    setNavOpen(false);
    window.scrollTo({ top: 0, left: 0 });
    window.history.pushState(null, '', routeForView('report-view', selectedBigBangId, next));
  }
  async function withBusy(fn: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    try { await fn(); } catch (error) { notify(error instanceof Error ? error.message : String(error)); }
    finally { setBusy(false); }
  }
  async function refreshBigBangs() {
    try {
      const rows = await Api.bigBangs();
      setBigBangs(rows);
      setBigBangError(null);
      if (selectedBigBangId && !rows.some((row) => row.id === selectedBigBangId)) setSelectedBigBangId(rows[0]?.id || null);
    } catch (error) {
      setBigBangs([]);
      setBigBangError(error instanceof Error ? error.message : String(error));
    }
  }
  async function loadWorkspace(bigBangId = selectedBigBangId) {
    if (!bigBangId) return;
    const payload = await Api.workspace(bigBangId);
    setWorkspace(payload);
    const selectedMv = payload.multiverses.find((item) => item.id === selectedMultiverseId) || payload.multiverses[0];
    setSelectedMultiverseId(selectedMv?.id || null);
    const ticks = selectedMv ? payload.ticks_by_multiverse[selectedMv.id] || [] : [];
    setSelectedTickId((current) => current && ticks.some((tick) => tick.id === current) ? current : ticks[ticks.length - 1]?.id || null);
    setInspector({ type: 'big_bang', payload: { item: payload.big_bang } });
  }
  async function openWorkspace(bigBangId: string) {
    await withBusy(async () => {
      setSelectedBigBangId(bigBangId);
      const payload = await Api.workspace(bigBangId);
      setWorkspace(payload);
      const selectedMv = payload.multiverses[0];
      setSelectedMultiverseId(selectedMv?.id || null);
      const ticks = selectedMv ? payload.ticks_by_multiverse[selectedMv.id] || [] : [];
      setSelectedTickId(ticks[ticks.length - 1]?.id || null);
      setInspector({ type: 'big_bang', payload: { item: payload.big_bang } });
      window.scrollTo({ top: 0, left: 0 });
      setView('workspace');
      window.history.pushState(null, '', routeForView('workspace', bigBangId));
    });
  }
  async function inspect(type: string, id: string) {
    await withBusy(async () => {
      const payload = await Api.inspect(type, id);
      setInspector({ type: payload.type || type, payload });
    });
  }
  async function updateStatus(action: 'start' | 'pause' | 'resume') {
    if (!selectedBigBangId) return notify('Select a Big Bang first');
    await withBusy(async () => {
      await Api.status(selectedBigBangId, action);
      await refreshBigBangs();
      await loadWorkspace(selectedBigBangId);
      notify(`${action} complete`);
    });
  }
  async function simulateNextTick() {
    if (!selectedMultiverseId) return notify('Select a multiverse first');
    await withBusy(async () => {
      const tick = await Api.simulateNextTick(selectedMultiverseId);
      await loadWorkspace(selectedBigBangId);
      setSelectedTickId(tick.id);
      const payload = await Api.inspect('tick', tick.id);
      setInspector({ type: payload.type || 'tick', payload });
      notify(`Simulated ${tick.ui_label}`);
    });
  }

  useEffect(() => {
    const onHash = () => {
      setReportRouteRef(initialReportRouteRef());
      setView(hashView());
    };
    window.addEventListener('hashchange', onHash);
    window.addEventListener('popstate', onHash);
    return () => {
      window.removeEventListener('hashchange', onHash);
      window.removeEventListener('popstate', onHash);
    };
  }, []);
  useEffect(() => {
    (async () => {
      try {
        const boot = await Api.bootstrap();
        setBootstrap(boot);
        await refreshBigBangs();
      } catch (error) {
        notify(error instanceof Error ? error.message : String(error));
      }
    })();
  }, []);
  useEffect(() => {
    if (view === 'workspace' && selectedBigBangId && !workspace) {
      loadWorkspace(selectedBigBangId).catch((error) => {
        notify(error instanceof Error ? error.message : String(error));
        setSelectedBigBangId(null);
        setWorkspace(null);
        setView('big-bangs');
        window.history.replaceState(null, '', routeForView('big-bangs'));
      });
    }
  }, [view, selectedBigBangId]);

  if (!bootstrap) {
    return <><div className="wf-app"><TopBar view={view} navigate={navigate} onMenu={() => setNavOpen(true)} /><AppDrawer open={navOpen} view={view} navigate={navigate} close={() => setNavOpen(false)} /><main className="wf-page"><div className="wf-empty">Loading WorldFork...</div></main></div><Toast message={toast} /></>;
  }

  return <>
    <div className="wf-app">
      <TopBar view={view} navigate={navigate} onMenu={() => setNavOpen(true)} workspace={workspace} bigBangs={bigBangs} busy={busy} updateStatus={updateStatus} simulateNextTick={simulateNextTick} />
      <AppDrawer open={navOpen} view={view} navigate={navigate} close={() => setNavOpen(false)} workspace={workspace} selectedBigBangId={selectedBigBangId} bigBangs={bigBangs} />
      {view === 'landing' && <Landing navigate={navigate} />}
      {view === 'big-bangs' && <BigBangSelection bootstrap={bootstrap} bigBangs={bigBangs} error={bigBangError} selectedBigBangId={selectedBigBangId} refresh={() => withBusy(refreshBigBangs)} openWorkspace={openWorkspace} createScenario={(scenarioId) => withBusy(async () => { const result = await Api.createScenarioBigBang(scenarioId); await refreshBigBangs(); await openWorkspace(result.big_bang_id); notify('Created from scenario bank'); })} navigate={navigate} />}
      {view === 'setup' && <Setup bootstrap={bootstrap} navigate={navigate} create={(payload) => withBusy(async () => { const created = await Api.createBigBang(payload); await refreshBigBangs(); await openWorkspace(created.id); notify('Created Big Bang'); })} />}
      {view === 'workspace' && <WorkspaceView bootstrap={bootstrap} workspace={workspace} selectedMultiverseId={selectedMultiverseId} selectedTickId={selectedTickId} inspector={inspector} busy={busy} selectMultiverse={(id) => { setSelectedMultiverseId(id); const ticks = workspace?.ticks_by_multiverse[id] || []; setSelectedTickId(ticks[ticks.length - 1]?.id || null); const mv = workspace?.multiverses.find((item) => item.id === id); if (mv) setInspector({ type: 'multiverse', payload: { item: mv } }); }} selectTick={(multiverseId, tickId) => { setSelectedMultiverseId(multiverseId); setSelectedTickId(tickId); inspect('tick', tickId); }} inspect={inspect} updateStatus={updateStatus} simulateNextTick={simulateNextTick} refresh={() => withBusy(async () => { await loadWorkspace(selectedBigBangId); notify('Workspace refreshed'); })} run={() => { if (selectedBigBangId) void withBusy(async () => { const job = await Api.createJob({ job_type: 'run_big_bang_until_complete', big_bang_id: selectedBigBangId, payload: { max_total_ticks: 12 } }); await loadWorkspace(selectedBigBangId); notify(job.error ? 'Run job created; enqueue failed, open Jobs to run it manually.' : 'Run 12 ticks job queued'); }); }} report={() => { if (selectedBigBangId) void withBusy(async () => { const job = await Api.createJob({ job_type: 'generate_final_big_bang_report', big_bang_id: selectedBigBangId, payload: { big_bang_id: selectedBigBangId } }); await loadWorkspace(selectedBigBangId); notify(job.error ? 'Report job created; enqueue failed, open Jobs to run it manually.' : 'Final report job queued'); }); }} notify={notify} />}
      {view === 'settings' && <SettingsPage bootstrap={bootstrap} notify={notify} />}
      {view === 'reports' && <ReportsPage bigBangs={bigBangs} selectedBigBangId={selectedBigBangId} setSelectedBigBangId={setSelectedBigBangId} openWorkspace={openWorkspace} openReportView={openReportView} notify={notify} />}
      {view === 'report-view' && <ReportView reportRef={reportRouteRef} navigate={navigate} notify={notify} />}
      {view === 'jobs' && <JobsPage notify={notify} openReportView={openReportView} navigate={navigate} />}
    </div>
    <Toast message={toast} />
  </>;
}

function hashView(): View {
  if (window.location.pathname === '/big-bangs') return 'big-bangs';
  if (window.location.pathname === '/big-bangs/new') return 'setup';
  if (window.location.pathname.startsWith('/workspace/')) return 'workspace';
  if (window.location.pathname === '/reports') return 'reports';
  if (window.location.pathname.startsWith('/reports/')) return 'report-view';
  if (window.location.pathname === '/jobs') return 'jobs';
  if (window.location.pathname === '/settings') return 'settings';
  const raw = window.location.hash.replace('#', '').trim() as View;
  return VIEWS.includes(raw) ? raw : 'landing';
}

function initialBigBangId(): string | null {
  const match = window.location.pathname.match(/^\/workspace\/([^/]+)/);
  return match?.[1] ? decodeURIComponent(match[1]) : localStorage.getItem('worldfork:selectedBigBangId');
}

function initialReportRouteRef(): ReportRouteRef {
  const versionMatch = window.location.pathname.match(/^\/reports\/version\/([^/]+)/);
  if (versionMatch?.[1]) return { kind: 'version', id: decodeURIComponent(versionMatch[1]) };
  const reportMatch = window.location.pathname.match(/^\/reports\/(?:report\/)?([^/]+)/);
  if (reportMatch?.[1] && reportMatch[1] !== 'version') return { kind: 'report', id: decodeURIComponent(reportMatch[1]) };
  return null;
}

function routeForView(view: View, bigBangId?: string | null, reportRef?: ReportRouteRef): string {
  if (view === 'big-bangs') return '/big-bangs';
  if (view === 'setup') return '/big-bangs/new';
  if (view === 'workspace' && bigBangId) return `/workspace/${encodeURIComponent(bigBangId)}`;
  if (view === 'reports') return '/reports';
  if (view === 'report-view' && reportRef) return `/reports/${reportRef.kind === 'version' ? 'version' : 'report'}/${encodeURIComponent(reportRef.id)}`;
  if (view === 'jobs') return '/jobs';
  if (view === 'settings') return '/settings';
  if (view === 'landing') return '/';
  return `/#${view}`;
}

function Icon({ name, size = 18, color = 'currentColor', stroke = 1.8 }: { name: IconName; size?: number; color?: string; stroke?: number }) {
  const d = ICON_PATHS[name];
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={d} /></svg>;
}

function WFLogo() {
  return <span className="wf-logo"><span className="wf-logo__dots" aria-hidden="true"><span className="wf-logo__dot d1" /><span className="wf-logo__dot d2" /><span className="wf-logo__dot d3" /><span className="wf-logo__dot d4" /><span className="wf-logo__dot d5" /><span className="wf-logo__dot d6" /><span className="wf-logo__dot center" /></span><span className="wf-logo__name">WorldFork</span></span>;
}

function TopBar(props: { view: View; navigate: (view: View) => void; onMenu: () => void; workspace?: WorkspacePayload | null; bigBangs?: BigBang[]; busy?: boolean; updateStatus?: (action: 'start' | 'pause' | 'resume') => void; simulateNextTick?: () => void }) {
  const activeCount = props.workspace?.multiverses.filter((item) => !['terminated', 'completed', 'frozen'].includes(statusClass(item.status))).length ?? props.bigBangs?.filter((item) => statusClass(item.status) === 'running').length ?? 0;
  const isWorkspace = props.view === 'workspace';
  const paused = statusClass(props.workspace?.big_bang.status) === 'paused';
  return <header className="wf-bar">
    <div className="wf-bar__left">
      <button className="wf-icon-btn" aria-label="Menu" onClick={props.onMenu}><Icon name="menu" size={20} /></button>
      <button className="wf-brand-btn" onClick={() => props.navigate('landing')} aria-label="WorldFork home"><WFLogo /></button>
      {isWorkspace && props.workspace && <div className="wf-crumbs"><span>Big Bangs</span><span>/</span><strong>{props.workspace.big_bang.name}</strong></div>}
    </div>
    {props.view === 'big-bangs' && <div className="wf-search" role="search"><Icon name="search" size={18} color="#5f6368" /><span>Search big bangs, tags, or topics</span><kbd>⌘K</kbd></div>}
    <div className="wf-bar__right">
      {(props.view === 'big-bangs' || props.view === 'setup' || props.view === 'workspace') && <StatusChip icon="clock" label="Sim Time" value={isWorkspace ? latestTime(props.workspace) : 'Ready'} live={isWorkspace && statusClass(props.workspace?.big_bang.status) === 'running'} />}
      {(props.view === 'big-bangs' || props.view === 'setup' || props.view === 'workspace') && <TimelineChip count={activeCount} />}
      {isWorkspace && <><button className="wf-btn wf-btn--primary" disabled={props.busy} onClick={() => props.updateStatus?.(paused ? 'resume' : 'start')}><Icon name="play" size={14} />{paused ? 'Resume' : 'Start'}</button><button className="wf-btn wf-btn--outline" disabled={props.busy || paused} onClick={() => props.updateStatus?.('pause')}><Icon name="pause" size={14} />Pause</button><button className="wf-btn wf-btn--outline" disabled={props.busy || paused} onClick={props.simulateNextTick}><Icon name="forward" size={14} />Step Tick</button></>}
      {props.view === 'landing' && <button className="wf-btn wf-btn--ghost" onClick={() => props.navigate('big-bangs')}>Past Big Bangs</button>}
      {props.view !== 'landing' && <span className="wf-avatar">A</span>}
    </div>
  </header>;
}

function AppDrawer({ open, view, navigate, close, workspace, selectedBigBangId, bigBangs = [] }: { open: boolean; view: View; navigate: (view: View) => void; close: () => void; workspace?: WorkspacePayload | null; selectedBigBangId?: string | null; bigBangs?: BigBang[] }) {
  const selectedBang = workspace?.big_bang || bigBangs.find((item) => item.id === selectedBigBangId);
  const navItems: Array<{ view: View; icon: IconName; label: string; body: string }> = [
    { view: 'landing', icon: 'sparkle', label: 'Home', body: 'Product overview and start point.' },
    { view: 'big-bangs', icon: 'grid', label: 'Simulations', body: 'Open existing simulation worlds.' },
    { view: 'setup', icon: 'plus', label: 'Setup', body: 'Paste scenario text and initialize a run.' },
    { view: 'workspace', icon: 'branch', label: 'Workspace', body: 'Run ticks, inspect branches, compare timelines.' },
    { view: 'reports', icon: 'chart', label: 'Reports', body: 'Generate final and multiverse reports.' },
    { view: 'jobs', icon: 'bot', label: 'Jobs', body: 'Inspect backend background work.' },
    { view: 'settings', icon: 'settings', label: 'Settings', body: 'Read backend config and model defaults.' },
  ];
  return <>
    <button className={`wf-drawer-backdrop ${open ? 'open' : ''}`} aria-label="Navigation backdrop" onClick={close} />
    <aside className={`wf-drawer ${open ? 'open' : ''}`} aria-hidden={!open}>
      <div className="wf-drawer-head"><WFLogo /><button className="wf-icon-btn" aria-label="Close navigation" onClick={close}><Icon name="close" size={18} /></button></div>
      <div className="wf-drawer-context">
        <span>Current place</span>
        <strong>{navItems.find((item) => item.view === view)?.label || 'WorldFork'}</strong>
        <p>{selectedBang ? `${selectedBang.name} · ${selectedBang.status}` : 'No simulation selected yet.'}</p>
      </div>
      <nav className="wf-drawer-nav" aria-label="Primary navigation">
        {navItems.map((item) => <button key={item.view} className={item.view === view ? 'active' : ''} onClick={() => navigate(item.view)}><Icon name={item.icon} size={17} /><span><strong>{item.label}</strong><small>{item.body}</small></span></button>)}
      </nav>
      <div className="wf-drawer-note"><Icon name="info" size={15} /><span>The drawer is the app map. Top-bar controls are shortcuts for the current task.</span></div>
    </aside>
  </>;
}

function StatusChip({ icon, label, value, live }: { icon: IconName; label: string; value: string; live?: boolean }) {
  return <div className="wf-bar-chip"><Icon name={icon} size={16} color="#5f6368" /><div><span>{label}</span><strong>{value}{live && <i className="wf-live-dot" />}</strong></div></div>;
}

function TimelineChip({ count }: { count: number }) {
  return <div className="wf-bar-chip wf-timeline-chip"><div><span>Open paths</span><strong>{count}</strong></div><Sparkline values={[2, 3, 2, 5, 4, 7, 6, Math.max(8, count)]} width={68} height={26} color="#1a73e8" /></div>;
}

function Sparkline({ values, color = '#1a73e8', width = 110, height = 28 }: { values: number[]; color?: string; width?: number; height?: number }) {
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = Math.max(1, max - min);
  const step = width / Math.max(1, values.length - 1);
  const points = values.map((value, index) => [index * step, height - 2 - ((value - min) / range) * (height - 4)]);
  const d = points.map((point, index) => `${index === 0 ? 'M' : 'L'}${point[0].toFixed(1)} ${point[1].toFixed(1)}`).join(' ');
  return <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="wf-spark"><path d={`${d} L${width} ${height} L0 ${height} Z`} fill={color} opacity="0.12" /><path d={d} fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

function Landing({ navigate }: { navigate: (view: View) => void }) {
  return <main className="wf-landing"><div className="wf-eyebrow"><span />Simulate. Branch. Understand.</div><h1>Simulate one scenario<br />across many <em>branching futures.</em></h1><p>Create a Big Bang, watch timelines fork into multiple futures,<br />and inspect why events, cohort shifts, and reports happen.</p><div className="wf-hero-actions"><button className="wf-btn wf-btn--primary wf-btn--lg" onClick={() => navigate('setup')}><Icon name="play" size={14} />Start Simulation</button><button className="wf-btn wf-btn--outline wf-btn--lg" onClick={() => navigate('big-bangs')}><Icon name="clock" size={14} />View Past Big Bangs</button></div><HeroBranches /><section className="wf-feature-grid"><FeatureCard icon="branch" tone="blue" title="Recursive Multiverse Timelines" body="One scenario branches into many futures across time. Compare outcomes and explore alternate possibilities." /><FeatureCard icon="shield" tone="green" title="Explainable Reasoning" body="Inspect the why behind every fork. See events, cohort shifts, and policy impacts in plain language." /><FeatureCard icon="chart" tone="yellow" title="Emotion + Sociology Graphs" body="Visualize public emotion, dependency chains, and social signals that shape each timeline." /></section><p className="wf-private"><Icon name="lock" size={14} color="#9aa0a6" />Your simulations are private and secure.</p></main>;
}

function HeroBranches() {
  const branches = [
    { color: '#4285f4', y: 40, label: 'M1.1', name: 'Fare Freeze', highlight: true },
    { color: '#34a853', y: 88, label: 'M1.2', name: 'Phased Rollout' },
    { color: '#8430ce', y: 138, label: 'M1.3', name: 'Employer Subsidy' },
    { color: '#f9ab00', y: 188, label: 'M1.4', name: 'Service Expansion' },
    { color: '#ea4335', y: 236, label: 'M2', name: 'Labor Escalation' },
  ];
  const ticks = ['T6', 'T7', 'T8', 'T9', 'T10'];
  return <div className="wf-hero-branches"><svg width="760" height="280" viewBox="0 0 760 280"><line x1="138" y1="138" x2="220" y2="138" stroke="#9aa0a6" strokeWidth="1.5" strokeLinecap="round" />{branches.map((branch) => <path key={branch.label} d={`M 244 138 C 270 138, 266 ${branch.y}, 290 ${branch.y}`} stroke={branch.color} strokeWidth="1.8" fill="none" strokeLinecap="round" />)}</svg><div className="wf-root-card"><span>Root Scenario</span><strong><Icon name="sparkle" size={14} color="#1a73e8" />Big Bang</strong><small>2025-05-20 14:32</small></div><div className="wf-t5-chip">T5</div>{branches.map((branch) => <div key={branch.label}>{ticks.map((tick, index) => <div key={`${branch.label}-${tick}`} className={`wf-demo-tick ${branch.highlight && tick === 'T7' ? 'active' : ''}`} style={{ left: 290 + index * 58, top: branch.y - 14, '--branch-color': branch.color } as CSSProperties}>{tick}</div>)}{ticks.slice(0, -1).map((_, index) => <span key={`${branch.label}-line-${index}`} className="wf-demo-tick-line" style={{ left: 334 + index * 58, top: branch.y - 1 }} />)}<span className="wf-demo-dots" style={{ left: 580, top: branch.y - 8 }}>···</span><div className="wf-demo-label" style={{ top: branch.y - 14 }}><strong style={{ color: branch.color }}>{branch.label}</strong><span>{branch.name}</span></div></div>)}</div>;
}

function FeatureCard({ icon, tone, title, body }: { icon: IconName; tone: string; title: string; body: string }) {
  return <article className="wf-card wf-feature"><div className={`wf-feature-icon ${tone}`}><Icon name={icon} size={22} /></div><h3>{title}</h3><p>{body}</p></article>;
}

function isTerminalStatus(status?: string): boolean {
  return ['completed', 'terminated'].includes(statusClass(status));
}

function allMultiversesTerminal(workspace?: WorkspacePayload | null): boolean {
  return Boolean(workspace?.multiverses.length) && workspace!.multiverses.every((item) => isTerminalStatus(item.status));
}

async function extractPdfText(file: File, onProgress?: (page: number, total: number) => void): Promise<string> {
  const pdfjsLib = await import('pdfjs-dist');
  pdfjsLib.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.mjs', import.meta.url).toString();
  const data = new Uint8Array(await file.arrayBuffer());
  const pdf = await pdfjsLib.getDocument({ data }).promise;
  const pages: string[] = [];
  for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
    onProgress?.(pageNumber, pdf.numPages);
    const page = await pdf.getPage(pageNumber);
    const content = await page.getTextContent();
    const text = content.items.map((item: any) => typeof item.str === 'string' ? item.str : '').filter(Boolean).join(' ');
    pages.push(`Page ${pageNumber}\n${text}`);
  }
  const extracted = pages.join('\n\n').trim();
  if (!extracted) throw new Error('No selectable text was found in this PDF. Scanned image PDFs need OCR before upload.');
  return extracted;
}

function normalizedTickOptions(current: string): string[] {
  return TICK_DURATION_OPTIONS.includes(current) ? TICK_DURATION_OPTIONS : [current, ...TICK_DURATION_OPTIONS];
}

function scenarioConfigDefaults(scenario: ScenarioBankItem, defaults: BootstrapPayload['defaults']): { tick_duration: string; max_ticks: number } {
  if (scenario.id === 'public_ai_deployment') return { tick_duration: '1 week', max_ticks: 12 };
  const tick_duration = scenario.tick_size || defaults.simulation_config.tick_duration;
  return {
    tick_duration,
    max_ticks: durationToTicks(scenario.duration, tick_duration) || defaults.simulation_config.max_ticks,
  };
}

function durationToTicks(duration?: string, tickSize?: string): number | null {
  const totalDays = durationToDays(duration);
  const tickDays = durationToDays(tickSize);
  if (!totalDays || !tickDays) return null;
  return Math.max(1, Math.ceil(totalDays / tickDays));
}

function durationToDays(value?: string): number | null {
  if (!value) return null;
  const match = value.toLowerCase().match(/(\d+(?:\.\d+)?)\s*(day|days|week|weeks|month|months|year|years)/);
  if (!match) return null;
  const count = Number(match[1]);
  const unit = match[2];
  if (unit.startsWith('day')) return count;
  if (unit.startsWith('week')) return count * 7;
  if (unit.startsWith('month')) return count * 30;
  if (unit.startsWith('year')) return count * 365;
  return null;
}

function BigBangSelection(props: { bootstrap: BootstrapPayload; bigBangs: BigBang[]; error: string | null; selectedBigBangId: string | null; refresh: () => void; openWorkspace: (id: string) => void; createScenario: (id: string) => void; navigate: (view: View) => void }) {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const counts = useMemo(() => props.bigBangs.reduce<Record<string, number>>((acc, item) => { const key = statusClass(item.status); acc[key] = (acc[key] || 0) + 1; return acc; }, {}), [props.bigBangs]);
  const filtered = props.bigBangs.filter((item) => {
    const itemStatus = statusClass(item.status);
    const statusMatches = statusFilter === 'all' || (statusFilter === 'completed' ? isTerminalStatus(item.status) : itemStatus === statusFilter);
    return (`${item.name} ${item.description || ''} ${JSON.stringify(item.scenario_input || {})}`).toLowerCase().includes(search.toLowerCase()) && statusMatches;
  });
  return <main className="wf-page"><section className="wf-page-head"><div><h1>Big Bangs</h1><p>Select or create a simulation scenario to explore complex system dynamics.</p></div><div className="wf-actions"><button className="wf-btn wf-btn--outline" onClick={props.refresh}><Icon name="refresh" size={14} />Refresh</button><button className="wf-btn wf-btn--primary" onClick={() => props.navigate('setup')}><Icon name="plus" size={14} />New Big Bang</button></div></section><section className="wf-stats"><StatTile icon="sparkle" tone="blue" num={props.bigBangs.length} label="Total" sub="Across local workspace" /><StatTile icon="play" tone="green" num={counts.running || 0} label="Running" sub="Active right now" /><StatTile icon="pause" tone="yellow" num={counts.paused || 0} label="Paused" sub="Awaiting input" /><StatTile icon="chart" tone="purple" num={(counts.completed || 0) + (counts.terminated || 0)} label="Completed" sub="Finished paths" /><StatTile icon="file" tone="orange" num={counts.draft || counts.created || 0} label="Draft" sub="Not yet running" /><StatTile icon="branch" tone="cyan" num={props.bootstrap.scenario_bank.scenarios.length} label="Templates" sub="Scenario bank" /></section><section className="wf-selection-layout"><aside className="wf-side"><div className="wf-filter-search"><Icon name="search" size={16} color="#5f6368" /><input placeholder="Search Big Bangs" value={search} onChange={(event) => setSearch(event.target.value)} /></div><SideGroup title="Status"><FilterButton label="All" count={props.bigBangs.length} active={statusFilter === 'all'} onClick={() => setStatusFilter('all')} /><FilterButton label="Running" count={counts.running || 0} active={statusFilter === 'running'} onClick={() => setStatusFilter('running')} /><FilterButton label="Paused" count={counts.paused || 0} active={statusFilter === 'paused'} onClick={() => setStatusFilter('paused')} /><FilterButton label="Completed" count={(counts.completed || 0) + (counts.terminated || 0)} active={statusFilter === 'completed'} onClick={() => setStatusFilter('completed')} /></SideGroup><SideGroup title="Scenario Bank"><div className="wf-scenario-mini-list">{props.bootstrap.scenario_bank.scenarios.slice(0, 8).map((scenario) => <ScenarioMini key={scenario.id} scenario={scenario} create={props.createScenario} />)}</div></SideGroup></aside><section className="wf-card wf-list-card"><div className="wf-list-head"><strong>{plural(filtered.length, 'result')}</strong><span>API-backed list</span></div>{props.error && <div className="wf-empty">Database unavailable: {props.error}</div>}<div className="wf-bang-list">{filtered.length ? filtered.map((item) => <BigBangRow key={item.id} item={item} active={item.id === props.selectedBigBangId} open={props.openWorkspace} />) : <div className="wf-empty">No Big Bangs match this view.</div>}</div></section></section></main>;
}

function StatTile({ icon, tone, num, label, sub }: { icon: IconName; tone: string; num: number; label: string; sub: string }) {
  return <article className="wf-stat"><div className={`wf-stat-icon ${tone}`}><Icon name={icon} size={20} /></div><div><strong>{num}</strong><span>{label}</span><small>{sub}</small></div></article>;
}

function SideGroup({ title, children }: { title: string; children: ReactNode }) { return <div className="wf-side-group"><h3>{title}</h3>{children}</div>; }
function FilterButton({ label, count, active, onClick }: { label: string; count: number; active: boolean; onClick: () => void }) { return <button className={`wf-filter-row ${active ? 'active' : ''}`} onClick={onClick}><span>{label}</span><small>{count}</small></button>; }
function ScenarioMini({ scenario, create }: { scenario: ScenarioBankItem; create: (id: string) => void }) { return <article className="wf-scenario-mini"><div><strong>{scenario.title || scenario.id}</strong><p>{firstWords(scenario.what_it_tests || scenario.description || scenario.initial_public_event || 'Scenario-bank option', 13)}</p></div><button className="wf-btn wf-btn--text" onClick={() => create(scenario.id)}>Use</button></article>; }

function BigBangRow({ item, active, open }: { item: BigBang; active: boolean; open: (id: string) => void }) {
  const text = item.description || (item.scenario_input as any)?.scenario_text || 'No scenario description has been saved yet.';
  return <article className={`wf-bang-row ${active ? 'active' : ''}`}><div className="wf-bang-icon"><Icon name="sparkle" size={24} /></div><div className="wf-bang-main"><div className="wf-bang-title"><strong>{item.name}</strong><Pill status={item.status} /></div><p>{firstWords(text, 24)}</p><div className="wf-chips"><Chip>v{item.current_config_version}</Chip><Chip>{fmtDate(item.created_at)}</Chip></div></div><div className="wf-bang-spark"><Sparkline values={[1, 2, 1, 3, 4, 3, 5, item.current_config_version + 5]} color="#1a73e8" /></div><div className="wf-row-actions"><button className="wf-btn wf-btn--primary" onClick={() => open(item.id)}><Icon name="open" size={14} />Open</button></div></article>;
}

function Setup({ bootstrap, navigate, create }: { bootstrap: BootstrapPayload; navigate: (view: View) => void; create: (payload: BigBangCreatePayload) => void }) {
  const [selectedScenario, setSelectedScenario] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [scenarioBody, setScenarioBody] = useState('');
  const [initializerPrompt, setInitializerPrompt] = useState('');
  const [pdfStatus, setPdfStatus] = useState('');
  const defaults = bootstrap.defaults;
  const [tickDuration, setTickDuration] = useState(defaults.simulation_config.tick_duration);
  const [maxTicks, setMaxTicks] = useState(String(defaults.simulation_config.max_ticks));
  function insertScenario(id = selectedScenario) { const scenario = bootstrap.scenario_bank.scenarios.find((item) => item.id === id); if (!scenario) return; const config = scenarioConfigDefaults(scenario, defaults); if (!name.trim()) setName(scenario.title || scenario.id); setScenarioBody(scenarioText(scenario)); setTickDuration(config.tick_duration); setMaxTicks(String(config.max_ticks)); }
  async function handlePdfUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setPdfStatus(`Parsing ${file.name}...`);
    try {
      const text = await extractPdfText(file, (page, total) => setPdfStatus(`Parsing ${file.name}: page ${page} of ${total}`));
      setScenarioBody((current) => current.trim() ? `${current.trim()}\n\n--- Extracted PDF: ${file.name} ---\n${text}` : text);
      if (!name.trim()) setName(file.name.replace(/\.pdf$/i, ''));
      setPdfStatus(`Parsed ${file.name} into ${text.split(/\s+/).filter(Boolean).length.toLocaleString()} words.`);
    } catch (error) {
      setPdfStatus(error instanceof Error ? error.message : String(error));
    } finally {
      event.target.value = '';
    }
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fd = new FormData(event.currentTarget);
    create({ name, description: description || null, scenario_text: scenarioBody, simulation_config: { tick_duration: tickDuration || defaults.simulation_config.tick_duration, max_ticks: Number(maxTicks || defaults.simulation_config.max_ticks) }, branch_policy: { max_branch_depth: Number(fd.get('max_branch_depth') || defaults.branch_policy.max_branch_depth), max_active_multiverses: Number(fd.get('max_active_multiverses') || defaults.branch_policy.max_active_multiverses), max_branches_per_tick: Number(fd.get('max_branches_per_tick') || defaults.branch_policy.max_branches_per_tick), branch_score_threshold: Number(fd.get('branch_score_threshold') || defaults.branch_policy.branch_score_threshold) }, use_initializer_agent: true, initializer_prompt: initializerPrompt || null });
  }
  return <main className="wf-page"><section className="wf-page-head"><div><h1>Set up a simulation</h1><p>Paste the scenario, choose time and branch defaults, then let the initialization agent build the actors, cohorts, and social graph.</p></div><button className="wf-btn wf-btn--outline" onClick={() => navigate('big-bangs')}>Cancel</button></section><section className="wf-setup-layout"><form className="wf-card wf-setup-form" onSubmit={submit}><div className="wf-form-section"><div className="wf-section-title"><span>1</span><div><h2>Scenario Prompt</h2><p>The backend receives the full scenario as plain text, including parsed PDF text.</p></div></div><div className="wf-form-grid"><Field label="Name"><input className="wf-input" required value={name} onChange={(event) => setName(event.target.value)} placeholder="City Transit Crisis" /></Field><Field label="Scenario template"><select className="wf-input" value={selectedScenario} onChange={(event) => { setSelectedScenario(event.target.value); insertScenario(event.target.value); }}><option value="">Blank prose scenario</option>{bootstrap.scenario_bank.scenarios.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.title || scenario.id}</option>)}</select></Field></div><Field label="Description"><input className="wf-input" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Short private label for this simulation" /></Field><Field label="Scenario text"><textarea className="wf-textarea" required rows={12} value={scenarioBody} onChange={(event) => setScenarioBody(event.target.value)} placeholder="Paste the full scenario or parsed PDF text here." /></Field><div className="wf-doc-note"><Icon name="upload" size={18} /><div><strong>Document context</strong><p>Upload a PDF or paste text. The backend still receives one long plain-text scenario string.</p>{pdfStatus && <small className="wf-upload-status">{pdfStatus}</small>}</div><label className="wf-btn wf-btn--outline"><input className="wf-file-input" type="file" accept="application/pdf" onChange={handlePdfUpload} />Upload PDF</label><button type="button" className="wf-btn wf-btn--outline" onClick={() => insertScenario()}>Insert selected scenario</button></div></div><div className="wf-form-section"><div className="wf-section-title"><span>2</span><div><h2>Simulation Basics</h2><p>These defaults come from `/api/frontend/bootstrap`.</p></div></div><div className="wf-form-grid three"><Field label="Tick duration"><select className="wf-input" name="tick_duration" value={tickDuration} onChange={(event) => setTickDuration(event.target.value)}>{normalizedTickOptions(tickDuration).map((option) => <option key={option} value={option}>{option}</option>)}</select></Field><Field label="Max ticks"><input className="wf-input" name="max_ticks" type="number" min="1" value={maxTicks} onChange={(event) => setMaxTicks(event.target.value)} /></Field><Field label="Max branches/tick"><input className="wf-input" name="max_branches_per_tick" type="number" min="0" defaultValue={defaults.branch_policy.max_branches_per_tick} /></Field><Field label="Max branch depth"><input className="wf-input" name="max_branch_depth" type="number" min="0" defaultValue={defaults.branch_policy.max_branch_depth} /></Field><Field label="Max active multiverses"><input className="wf-input" name="max_active_multiverses" type="number" min="1" defaultValue={defaults.branch_policy.max_active_multiverses} /></Field><Field label="Branch threshold"><input className="wf-input" name="branch_score_threshold" type="number" min="0" max="1" step="0.01" defaultValue={defaults.branch_policy.branch_score_threshold} /></Field></div></div><div className="wf-form-section"><div className="wf-section-title"><span>3</span><div><h2>Initialization Agent</h2><p>Mandatory: the initializer derives actors, cohorts, graph layers, and social context from the prose plus the structured simulation config above.</p></div></div><div className="wf-doc-note"><Icon name="sparkle" size={18} /><div><strong>Initialization is always on</strong><p>The backend receives <code>use_initializer_agent: true</code>. The controls in Simulation Basics are submitted directly as API config, not inferred by the agent.</p></div></div><Field label="Initializer prompt override"><textarea className="wf-textarea" rows={5} value={initializerPrompt} onChange={(event) => setInitializerPrompt(event.target.value)} placeholder="Optional extra instructions for initialization only." /></Field></div><div className="wf-form-actions"><button type="button" className="wf-btn wf-btn--outline" onClick={() => navigate('big-bangs')}>Back</button><button type="submit" className="wf-btn wf-btn--primary"><Icon name="sparkle" size={14} />Create Big Bang</button></div></form><aside className="wf-setup-side"><ConfigCard title="Model defaults" rows={Object.entries(defaults.model_config || {}).slice(0, 8).map(([key, value]) => [key, value])} /><ConfigCard title="Available labels" rows={[["Emotions", bootstrap.labels.emotions.length], ["Graph layers", bootstrap.labels.graph_layers.length], ["Sociology models", bootstrap.labels.sociology_models.length], ["Tools", bootstrap.labels.tools.length]]} /><div className="wf-card wf-side-callout"><Icon name="info" size={18} /><p>Keep the prompt long if needed. The initialization agent is expected to build the full social world from this context.</p></div></aside></section></main>;
}

function Field({ label, children }: { label: string; children: ReactNode }) { return <label className="wf-field"><span>{label}</span>{children}</label>; }
function ConfigCard({ title, rows }: { title: string; rows: Array<[string, unknown]> }) { return <article className="wf-card wf-config-card"><h3>{title}</h3>{rows.map(([key, value]) => <div className="wf-kv" key={key}><span>{key.replaceAll('_', ' ')}</span><strong>{String(value)}</strong></div>)}</article>; }

function SettingsPage({ bootstrap, notify }: { bootstrap: BootstrapPayload; notify: (message: string) => void }) {
  const [settings, setSettings] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    Api.settings()
      .then((payload) => { if (alive) setSettings(payload); })
      .catch((error) => notify(error instanceof Error ? error.message : String(error)))
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  const defaults = bootstrap.defaults;
  const agentModels = settings?.agent_models && typeof settings.agent_models === 'object' ? Object.entries(settings.agent_models) : [];
  return <main className="wf-page">
    <section className="wf-page-head">
      <div><h1>Settings</h1><p>Backend configuration surfaced directly from existing APIs.</p></div>
      <span className="wf-readonly"><Icon name="lock" size={14} />Read-only from backend config</span>
    </section>
    {loading && <div className="wf-empty">Loading settings...</div>}
    {!loading && !settings && <div className="wf-empty">Settings could not be loaded.</div>}
    {settings && <section className="wf-page-grid">
      <div className="wf-page-main">
        <div className="wf-callout"><Icon name="info" size={18} /><div><strong>No local editing yet</strong><p>This page intentionally mirrors `/api/settings` and `/api/frontend/bootstrap`. Mutation is hidden until the backend exposes safe update routes.</p></div></div>
        <div className="wf-inline-grid">
          <ConfigCard title="Application" rows={[["App name", settings.app_name], ["Provider", settings.default_llm_provider], ["Default model", settings.default_model]]} />
          <ConfigCard title="OpenAI-compatible provider" rows={[["Base URL", settings.openrouter_base_url], ["Chat endpoint", settings.openrouter_chat_completions_url]]} />
          <ConfigCard title="Storage" rows={[["Artifact root", settings.artifact_root], ["Source of truth", settings.source_of_truth_dir]]} />
          <ConfigCard title="Bootstrap defaults" rows={[["Tick duration", defaults.simulation_config.tick_duration], ["Max ticks", defaults.simulation_config.max_ticks], ["Max branches/tick", defaults.branch_policy.max_branches_per_tick], ["Branch threshold", defaults.branch_policy.branch_score_threshold], ["Max active multiverses", defaults.branch_policy.max_active_multiverses]]} />
        </div>
        <section className="wf-card wf-settings-panel">
          <h2>Per-agent model mapping</h2>
          <div className="wf-config-list">{agentModels.length ? agentModels.map(([key, value]) => <div className="wf-config-row" key={key}><span>{key.replaceAll('_', ' ')}</span><strong>{String(value)}</strong></div>) : <div className="wf-empty compact">No per-agent model mapping returned.</div>}</div>
        </section>
      </div>
      <aside className="wf-page-side">
        <ConfigCard title="Label coverage" rows={[["Emotions", bootstrap.labels.emotions.length], ["Graph layers", bootstrap.labels.graph_layers.length], ["Sociology models", bootstrap.labels.sociology_models.length], ["Tools", bootstrap.labels.tools.length], ["Scenario templates", bootstrap.scenario_bank.scenarios.length]]} />
        <section className="wf-card wf-settings-panel">
          <h2>Job types</h2>
          <div className="wf-chips">{bootstrap.job_types.map((type) => <Chip key={type} tone="blue">{type}</Chip>)}</div>
        </section>
      </aside>
    </section>}
  </main>;
}

function ReportsPage({ bigBangs, selectedBigBangId, setSelectedBigBangId, openWorkspace, openReportView, notify }: { bigBangs: BigBang[]; selectedBigBangId: string | null; setSelectedBigBangId: (id: string | null) => void; openWorkspace: (id: string) => Promise<void>; openReportView: (kind: 'report' | 'version', id: string) => void; notify: (message: string) => void }) {
  const [selectedId, setSelectedId] = useState(selectedBigBangId || bigBangs[0]?.id || '');
  const [workspace, setWorkspace] = useState<WorkspacePayload | null>(null);
  const [reports, setReports] = useState<any[]>([]);
  const [selectedReport, setSelectedReport] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const selectedBang = bigBangs.find((item) => item.id === selectedId);
  const finalReportReady = allMultiversesTerminal(workspace);

  async function load(id = selectedId) {
    if (!id) return;
    setLoading(true);
    try {
      const [workspacePayload, reportRows] = await Promise.all([Api.workspace(id), Api.reports(id)]);
      setWorkspace(workspacePayload);
      setReports(Array.isArray(reportRows) ? reportRows : []);
      setSelectedBigBangId(id);
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error));
      setWorkspace(null);
      setReports([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!selectedId && bigBangs[0]?.id) setSelectedId(bigBangs[0].id);
  }, [bigBangs.length]);

  useEffect(() => {
    if (selectedId) void load(selectedId);
  }, [selectedId]);

  async function generateFinalReport() {
    if (!selectedId) return;
    if (!finalReportReady) return notify('Final report requires all multiverses to be terminal.');
    setLoading(true);
    try {
      const job = await Api.createJob({ job_type: 'generate_final_big_bang_report', big_bang_id: selectedId, payload: { big_bang_id: selectedId } });
      await load(selectedId);
      notify(job.error ? 'Final report job created; enqueue failed, open Jobs to run it manually.' : 'Final report job queued');
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error));
    } finally {
      setLoading(false);
    }
  }

  async function generateMultiverseReport(multiverseId: string) {
    setLoading(true);
    try {
      const job = await Api.createJob({ job_type: 'generate_multiverse_report', big_bang_id: selectedId, payload: { multiverse_id: multiverseId } });
      await load(selectedId);
      notify(job.error ? 'Multiverse report job created; enqueue failed, open Jobs to run it manually.' : 'Multiverse report job queued');
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error));
    } finally {
      setLoading(false);
    }
  }

  async function inspectReport(reportId: string) {
    setLoading(true);
    try {
      const payload = await Api.inspect('report', reportId);
      setSelectedReport(payload);
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error));
    } finally {
      setLoading(false);
    }
  }

  const reportRows = reports.length ? reports : workspace?.reports || [];
  return <main className="wf-page">
    <section className="wf-page-head">
      <div><h1>Reports</h1><p>Generate and inspect final and per-multiverse reports from backend report APIs.</p></div>
      <div className="wf-actions"><button className="wf-btn wf-btn--outline" disabled={!selectedId || loading} onClick={() => void load(selectedId)}><Icon name="refresh" size={14} />Refresh</button><button className="wf-btn wf-btn--primary" disabled={!selectedId || loading || !finalReportReady} onClick={generateFinalReport}><Icon name="file" size={14} />Generate Final Report</button></div>
    </section>
    {!bigBangs.length && <div className="wf-empty">Create a Big Bang first, then reports will appear here.</div>}
    {!!bigBangs.length && <section className="wf-page-grid">
      <div className="wf-page-main">
        <section className="wf-card wf-control-panel">
          <Field label="Selected Big Bang"><select className="wf-input" value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>{bigBangs.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
          <div className="wf-actions"><button className="wf-btn wf-btn--outline" disabled={!selectedId || loading} onClick={() => selectedId && void openWorkspace(selectedId)}><Icon name="open" size={14} />Open Workspace</button><span className="wf-muted-text">{selectedBang ? selectedBang.status : 'No Big Bang selected'}</span></div>
        </section>
        <div className="wf-stats wf-stats--compact">
          <StatTile icon="file" tone="blue" num={reportRows.length} label="Reports" sub="current Big Bang" />
          <StatTile icon="branch" tone="green" num={workspace?.multiverses.length || 0} label="Multiverses" sub="available for report" />
          <StatTile icon="bot" tone="purple" num={workspace?.jobs.length || 0} label="Jobs" sub="background work" />
          <StatTile icon="clock" tone="orange" num={workspace?.latest_ticks.length || 0} label="Recent ticks" sub="workspace snapshot" />
        </div>
        <section className="wf-card wf-list-card">
          <div className="wf-list-head"><strong>Report rows</strong><span>{loading ? 'Loading...' : `${reportRows.length} records`}</span></div>
          <div className="wf-card-list">{reportRows.length ? reportRows.map((report) => <article className="wf-report-row" key={report.id}><div><div className="wf-row-title"><strong>{reportTitle(report)}</strong><Pill status={report.status || 'created'} /></div><p>{firstWords(report.summary || report.description || report.error || 'No summary returned yet.', 22)}</p><div className="wf-row-meta"><span>{fmtDate(report.created_at)}</span><span>{report.current_version ? `v${report.current_version}` : 'no version'}</span><span>{report.multiverse_id ? `timeline ${shortId(report.multiverse_id)}` : 'final scope'}</span></div></div><div className="wf-row-actions"><button className="wf-btn wf-btn--primary" disabled={!report.current_version} onClick={() => openReportView('report', report.id)}><Icon name="open" size={14} />View</button><button className="wf-btn wf-btn--outline" onClick={() => void inspectReport(report.id)}><Icon name="eye" size={14} />Details</button></div></article>) : <div className="wf-empty compact">No reports for this Big Bang yet.</div>}</div>
        </section>
        <section className="wf-card wf-settings-panel">
          <h2>Multiverse report actions</h2>
          <div className="wf-card-list">{workspace?.multiverses.length ? workspace.multiverses.map((mv) => <article className="wf-report-row" key={mv.id}><div><div className="wf-row-title"><strong>{mv.ui_label}</strong><Pill status={mv.status} /></div><p>{firstWords(mv.branch_reason || 'Root timeline report target.', 24)}</p><div className="wf-row-meta"><span>depth {mv.depth}</span><span>{mv.fork_tick_index == null ? 'root' : `fork T${mv.fork_tick_index}`}</span></div></div><button className="wf-btn wf-btn--outline" disabled={loading} onClick={() => void generateMultiverseReport(mv.id)}><Icon name="file" size={14} />Generate</button></article>) : <div className="wf-empty compact">Load a workspace to generate multiverse reports.</div>}</div>
        </section>
      </div>
      <aside className="wf-page-side">
        <ReportInspector report={selectedReport} openReportView={openReportView} />
      </aside>
    </section>}
  </main>;
}

function ReportInspector({ report, openReportView }: { report: any | null; openReportView: (kind: 'report' | 'version', id: string) => void }) {
  const root = report?.report || report?.item || report;
  const versions = report?.versions || report?.report_versions || root?.versions || [];
  return <section className="wf-card wf-detail-panel">
    <h2>Report inspector</h2>
    {!report && <div className="wf-empty compact">Select a report row to inspect its versions and artifacts.</div>}
    {report && <><ConfigCard title="Report" rows={[["Type", root?.report_type || root?.type || 'report'], ["Status", root?.status || 'n/a'], ["ID", shortId(root?.id)], ["Created", fmtDate(root?.created_at)], ["Updated", fmtDate(root?.updated_at)]]} />{root?.id && <button className="wf-btn wf-btn--primary wf-full-btn" onClick={() => openReportView('report', root.id)}><Icon name="open" size={14} />Open report view</button>}<div className="wf-artifact-list"><strong>Versions and artifacts</strong>{Array.isArray(versions) && versions.length ? versions.map((version: any) => <div className="wf-artifact-row" key={version.id || version.version || JSON.stringify(version).slice(0, 24)}><span>v{version.version || shortId(version.id)}</span><div><button className="wf-artifact-chip as-button" onClick={() => openReportView('version', version.id)}>View</button>{artifactChip('Markdown', version.markdown_artifact_id || version.markdown_id)}{artifactChip('PDF', version.pdf_artifact_id || version.pdf_id)}</div></div>) : <div className="wf-empty compact">No report versions returned.</div>}</div><details className="wf-raw"><summary>Raw report payload</summary><pre>{JSON.stringify(report, null, 2)}</pre></details></>}
  </section>;
}

function ReportView({ reportRef, navigate, notify }: { reportRef: ReportRouteRef; navigate: (view: View) => void; notify: (message: string) => void }) {
  const [payload, setPayload] = useState<any | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(reportRef?.kind === 'version' ? reportRef.id : null);
  const [markdown, setMarkdown] = useState('');
  const [loading, setLoading] = useState(false);

  async function load() {
    if (!reportRef) return;
    setLoading(true);
    setMarkdown('');
    try {
      const next = await Api.inspect(reportRef.kind === 'version' ? 'report_version' : 'report', reportRef.id);
      setPayload(next);
      const versions = reportVersions(next);
      const preferred = reportRef.kind === 'version'
        ? versions.find((version) => String(version.id) === reportRef.id) || next.item
        : versions[0];
      setSelectedVersionId(preferred?.id || null);
      if (preferred?.markdown_artifact_id) setMarkdown(await Api.artifactText(String(preferred.markdown_artifact_id)));
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error));
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [reportRef?.kind, reportRef?.id]);

  async function selectVersion(version: any) {
    setSelectedVersionId(version.id);
    setMarkdown('');
    try {
      if (version.markdown_artifact_id) setMarkdown(await Api.artifactText(String(version.markdown_artifact_id)));
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error));
    }
  }

  if (!reportRef) return <main className="wf-page"><div className="wf-empty">No report was selected. Open Reports or inspect a completed report job.</div></main>;
  const report = payload?.report || (payload?.type === 'report' ? payload.item : null) || {};
  const versions = reportVersions(payload);
  const selectedVersion = versions.find((version) => String(version.id) === selectedVersionId) || versions[0] || (payload?.type === 'report_version' ? payload.item : null);
  return <main className="wf-page wf-report-page">
    <section className="wf-page-head">
      <div><h1>{selectedVersion?.title || reportTitle(report)}</h1><p>{report.report_type ? `${report.report_type} · ${report.status || 'status unknown'}` : 'Report reader'}</p></div>
      <div className="wf-actions"><button className="wf-btn wf-btn--outline" onClick={() => navigate('reports')}><Icon name="list" size={14} />Reports</button><button className="wf-btn wf-btn--outline" disabled={loading} onClick={() => void load()}><Icon name="refresh" size={14} />Refresh</button>{selectedVersion?.pdf_artifact_id && artifactChip('Open PDF', selectedVersion.pdf_artifact_id)}</div>
    </section>
    {loading && <div className="wf-empty">Loading report...</div>}
    {!loading && <section className="wf-report-reader-layout">
      <aside className="wf-card wf-report-version-panel">
        <h2>Versions</h2>
        {versions.length ? versions.map((version) => <button key={version.id} className={version.id === selectedVersion?.id ? 'active' : ''} onClick={() => void selectVersion(version)}><strong>v{version.version}</strong><span>{fmtDate(version.created_at)}</span></button>) : <div className="wf-empty compact">No versions returned.</div>}
        {selectedVersion && <ConfigCard title="Selected version" rows={[["Version", selectedVersion.version || 'n/a'], ["ID", shortId(selectedVersion.id)], ["Markdown", selectedVersion.markdown_artifact_id ? shortId(selectedVersion.markdown_artifact_id) : 'none'], ["PDF", selectedVersion.pdf_artifact_id ? shortId(selectedVersion.pdf_artifact_id) : 'none']]} />}
      </aside>
      <article className="wf-card wf-report-reader">
        {markdown ? <MarkdownDocument text={markdown} /> : <div className="wf-empty">No markdown artifact is available for this report version.</div>}
      </article>
    </section>}
  </main>;
}

function MarkdownDocument({ text }: { text: string }) {
  return <div className="wf-markdown-doc">{text.split(/\n{2,}/).map((block, index) => renderMarkdownBlock(block, index))}</div>;
}

function renderMarkdownBlock(block: string, index: number): ReactNode {
  const trimmed = block.trim();
  if (!trimmed) return null;
  if (trimmed.startsWith('# ')) return <h1 key={index}>{trimmed.slice(2)}</h1>;
  if (trimmed.startsWith('## ')) return <h2 key={index}>{trimmed.slice(3)}</h2>;
  if (trimmed.startsWith('### ')) return <h3 key={index}>{trimmed.slice(4)}</h3>;
  const lines = trimmed.split('\n');
  if (lines.every((line) => line.trim().startsWith('- '))) {
    return <ul key={index}>{lines.map((line, lineIndex) => <li key={lineIndex}>{line.trim().slice(2)}</li>)}</ul>;
  }
  return <p key={index}>{lines.join(' ')}</p>;
}

function JobsPage({ notify, openReportView, navigate }: { notify: (message: string) => void; openReportView: (kind: 'report' | 'version', id: string) => void; navigate: (view: View) => void }) {
  const [jobs, setJobs] = useState<any[]>([]);
  const [types, setTypes] = useState<string[]>([]);
  const [selectedJob, setSelectedJob] = useState<any | null>(null);
  const [selectedJobReports, setSelectedJobReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const [jobRows, typeRows] = await Promise.all([Api.jobs(), Api.jobTypes()]);
      setJobs(Array.isArray(jobRows) ? jobRows : []);
      setTypes(Array.isArray(typeRows) ? typeRows : []);
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  async function runJob(job: any) {
    setLoading(true);
    try {
      await Api.runJob(job.id);
      await load();
      notify('Job run requested');
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error));
    } finally {
      setLoading(false);
    }
  }

  async function inspectJob(job: any) {
    setLoading(true);
    try {
      const payload = await Api.inspect('job', job.id);
      setSelectedJob(payload);
      const versionIds = reportVersionIdsFromJob(payload.item || payload);
      const reportPayloads = await Promise.all(versionIds.slice(0, 12).map((id) => Api.inspect('report_version', id).catch(() => null)));
      setSelectedJobReports(reportPayloads.filter(Boolean));
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error));
      setSelectedJobReports([]);
    } finally {
      setLoading(false);
    }
  }

  const statusCounts = jobs.reduce((acc, job) => ({ ...acc, [statusClass(job.status)]: (acc[statusClass(job.status)] || 0) + 1 }), {} as Record<string, number>);
  return <main className="wf-page">
    <section className="wf-page-head">
      <div><h1>Jobs</h1><p>Recent backend jobs and constrained run/retry actions.</p></div>
      <button className="wf-btn wf-btn--outline" disabled={loading} onClick={() => void load()}><Icon name="refresh" size={14} />Refresh</button>
    </section>
    <section className="wf-page-grid">
      <div className="wf-page-main">
        <div className="wf-stats wf-stats--compact">
          <StatTile icon="bot" tone="blue" num={jobs.length} label="Jobs" sub="recent rows" />
          <StatTile icon="clock" tone="orange" num={statusCounts.queued || 0} label="Queued" sub="runnable" />
          <StatTile icon="activity" tone="green" num={statusCounts.running || 0} label="Running" sub="active or retryable" />
          <StatTile icon="shield" tone="purple" num={(statusCounts.succeeded || 0) + (statusCounts.completed || 0) + (statusCounts.failed || 0)} label="Terminal" sub="succeeded or failed" />
        </div>
        <section className="wf-card wf-settings-panel">
          <h2>Available job types</h2>
          <div className="wf-chips">{types.length ? types.map((type) => <Chip key={type} tone="blue">{type}</Chip>) : <span className="wf-muted-text">No job types returned.</span>}</div>
        </section>
        <section className="wf-card wf-list-card">
          <div className="wf-list-head"><strong>Recent jobs</strong><span>{loading ? 'Loading...' : `${jobs.length} records`}</span></div>
          <div className="wf-card-list">{jobs.length ? jobs.map((job) => <article className="wf-report-row" key={job.id}><div><div className="wf-row-title"><strong>{jobDisplayName(job.job_type || job.type)}</strong><Pill status={job.status || 'queued'} /></div><p>{jobSummary(job)}</p><div className="wf-row-meta"><span>{job.big_bang_id ? 'Simulation scoped' : 'global'}</span><span>{fmtDate(job.created_at)}</span></div></div><div className="wf-row-actions"><button className="wf-btn wf-btn--outline" onClick={() => void inspectJob(job)}><Icon name="eye" size={14} />Inspect</button><button className="wf-btn wf-btn--primary" disabled={loading || !['queued', 'running'].includes(statusClass(job.status))} onClick={() => void runJob(job)}><Icon name="play" size={14} />Run</button></div></article>) : <div className="wf-empty compact">No jobs returned yet.</div>}</div>
        </section>
      </div>
      <aside className="wf-page-side">
        <section className="wf-card wf-detail-panel">
          <h2>Job inspector</h2>
          {!selectedJob && <div className="wf-empty compact">Inspect a job to see status, progress, and generated report links.</div>}
          {selectedJob && <><ConfigCard title="Job" rows={[["Type", jobDisplayName(selectedJob.job?.job_type || selectedJob.item?.job_type || selectedJob.job_type)], ["Status", selectedJob.job?.status || selectedJob.item?.status || selectedJob.status || 'n/a'], ["ID", shortId(selectedJob.job?.id || selectedJob.item?.id || selectedJob.id)], ["Created", fmtDate(selectedJob.job?.created_at || selectedJob.item?.created_at || selectedJob.created_at)]]} /><JobResultSummary job={selectedJob.item || selectedJob} reports={selectedJobReports} openReportView={openReportView} navigate={navigate} /><details className="wf-raw"><summary>Raw job payload</summary><pre>{JSON.stringify(selectedJob, null, 2)}</pre></details></>}
        </section>
      </aside>
    </section>
  </main>;
}

function JobResultSummary({ job, reports, openReportView, navigate }: { job: any; reports: any[]; openReportView: (kind: 'report' | 'version', id: string) => void; navigate: (view: View) => void }) {
  const result = job?.result || {};
  const versionIds = reportVersionIdsFromJob(job);
  return <section className="wf-job-result">
    <h3>Result</h3>
    <p>{jobSummary(job)}</p>
    <div className="wf-kv-list compact">
      {result.ticks_run != null && <div><span>Ticks run</span><strong>{result.ticks_run}</strong></div>}
      {result.latest_tick_label && <div><span>Latest tick</span><strong>{result.latest_tick_label}</strong></div>}
      {result.stopped_reason && <div><span>Stopped reason</span><strong>{result.stopped_reason}</strong></div>}
      {result.progress?.percent != null && <div><span>Progress</span><strong>{result.progress.percent}%</strong></div>}
    </div>
    {!!versionIds.length && <div className="wf-report-output-list">
      <strong>Generated reports</strong>
      {reports.length ? reports.map((payload) => {
        const version = payload.item || payload.version || payload;
        const report = payload.report || {};
        return <article key={version.id} className="wf-report-output">
          <div><strong>{version.title || report.report_type || 'Report version'}</strong><span>{report.report_type || 'report'} · v{version.version || shortId(version.id)}</span></div>
          <button className="wf-btn wf-btn--primary" onClick={() => openReportView('version', version.id)}><Icon name="open" size={14} />View report</button>
        </article>;
      }) : versionIds.map((id) => <article key={id} className="wf-report-output"><div><strong>Report version</strong><span>{shortId(id)}</span></div><button className="wf-btn wf-btn--primary" onClick={() => openReportView('version', id)}><Icon name="open" size={14} />View report</button></article>)}
      {job?.big_bang_id && <button className="wf-btn wf-btn--text" onClick={() => navigate('reports')}>Open all reports</button>}
    </div>}
    {!versionIds.length && <div className="wf-empty compact">This job has not produced a report version yet.</div>}
  </section>;
}

function WorkspaceView(props: { bootstrap: BootstrapPayload; workspace: WorkspacePayload | null; selectedMultiverseId: string | null; selectedTickId: string | null; inspector: InspectorState; busy: boolean; selectMultiverse: (id: string) => void; selectTick: (multiverseId: string, tickId: string) => void; inspect: (type: string, id: string) => void; updateStatus: (action: 'start' | 'pause' | 'resume') => void; simulateNextTick: () => void; refresh: () => void; run: () => void; report: () => void; notify: (message: string) => void }) {
  if (!props.workspace) return <main className="wf-page"><div className="wf-empty">No workspace loaded. Select a Big Bang first.</div></main>;
  const workspace = props.workspace;
  const selectedMv = workspace.multiverses.find((item) => item.id === props.selectedMultiverseId) || workspace.multiverses[0];
  const selectedTicks = selectedMv ? workspace.ticks_by_multiverse[selectedMv.id] || [] : [];
  const selectedTick = selectedTicks.find((tick) => tick.id === props.selectedTickId) || selectedTicks[selectedTicks.length - 1];
  const paused = statusClass(workspace.big_bang.status) === 'paused';
  const reportReady = allMultiversesTerminal(workspace);
  return <section className="wf-workspace"><ActivityRail workspace={workspace} inspect={props.inspect} /><main className="wf-workspace-main"><section className="wf-workspace-head"><div><h1>{workspace.big_bang.name}</h1><p>{workspace.big_bang.status} · {plural(workspace.multiverses.length, 'timeline')} · {plural(workspace.latest_ticks.length, 'recent tick')}</p></div><div className="wf-actions"><button className="wf-btn wf-btn--outline" disabled={props.busy} onClick={props.refresh}><Icon name="refresh" size={14} />Refresh</button><button className="wf-btn wf-btn--outline" disabled={props.busy || paused} onClick={props.run}>Run 12 ticks</button><button className="wf-btn wf-btn--outline" disabled={props.busy || !reportReady} onClick={props.report}>Report job</button></div></section><JobProgressStrip jobs={workspace.jobs} /><WorkspaceTruncationNotice workspace={workspace} /><section className="wf-card wf-timeline-panel"><div className="wf-panel-head"><div><h2>Timeline paths</h2><p>Each rail is a multiverse path; forks and ticks come from lineage and tick API data.</p></div><div className="wf-chip-row"><Chip tone="blue">Emotion</Chip><Chip tone="green">Dependency</Chip><Chip tone="purple">Sociology</Chip></div></div><TimelineGraph workspace={workspace} selectedMultiverseId={props.selectedMultiverseId} selectedTickId={props.selectedTickId} selectMultiverse={props.selectMultiverse} selectTick={props.selectTick} /></section><TickOverview tick={selectedTick} workspace={workspace} inspector={props.inspector} /><SignalGrid workspace={workspace} /></main><InspectorPanel workspace={workspace} selectedMv={selectedMv} selectedTick={selectedTick} inspector={props.inspector} inspect={props.inspect} selectTick={props.selectTick} simulateNextTick={props.simulateNextTick} busy={props.busy} /></section>;
}

function JobProgressStrip({ jobs }: { jobs: any[] }) {
  const recent = jobs.find((job) => ['queued', 'running'].includes(statusClass(job.status)));
  if (!recent) return null;
  return <section className="wf-job-strip"><Icon name="bot" size={16} /><div><strong>{jobDisplayName(recent.job_type)}</strong><span>{recent.status} · {jobSummary(recent)}</span></div></section>;
}

function WorkspaceTruncationNotice({ workspace }: { workspace: WorkspacePayload }) {
  const truncation = (workspace as any).truncation || {};
  const messages = [
    truncation.ticks_source_truncated ? `Timeline rails use the latest ${truncation.ticks_source_limit} of ${truncation.total_ticks} ticks.` : '',
    truncation.latest_ticks_truncated ? `Recent tick summaries show ${truncation.latest_ticks_limit} ticks.` : '',
  ].filter(Boolean);
  if (!messages.length) return null;
  return <div className="wf-callout wf-truncation"><Icon name="info" size={18} /><div><strong>Workspace snapshot truncated</strong><p>{messages.join(' ')}</p></div></div>;
}

function ActivityRail({ workspace, inspect }: { workspace: WorkspacePayload; inspect: (type: string, id: string) => void }) {
  const [filter, setFilter] = useState<ActivityFilter>('all');
  const countKind = (kind: ActivityFilter) => kind === 'all' ? workspace.activity.length : workspace.activity.filter((item) => item.kind === kind).length;
  const buckets = [
    ['all', 'All Activity', countKind('all'), 'activity'],
    ['tick', 'Ticks', countKind('tick'), 'clock'],
    ['tool_call', 'Tool Calls', countKind('tool_call'), 'bot'],
    ['job', 'Jobs', countKind('job'), 'file'],
    ['report', 'Reports', countKind('report'), 'chart'],
  ] as Array<[ActivityFilter, string, number, IconName]>;
  const visible = workspace.activity.filter((item) => filter === 'all' || item.kind === filter);
  return <aside className="wf-activity-rail"><div className="wf-rail-head"><strong>Activity</strong></div>{buckets.map(([key, label, count, icon]) => <button key={key} className={`wf-rail-item ${filter === key ? 'active' : ''}`} onClick={() => setFilter(key)}><Icon name={icon} size={16} /><span>{label}</span><small>{count}</small></button>)}<div className="wf-activity-list">{visible.slice(0, 10).map((item) => <button key={`${item.kind}-${item.id}`} className="wf-activity-card" onClick={() => inspect(item.kind.replace(/-/g, '_'), item.id)}><strong>{item.kind === 'job' ? jobDisplayName(item.label) : item.label}</strong><span>{item.kind.replaceAll('_', ' ')} · {item.status}</span><small>{fmtDate(item.created_at)}</small></button>)}{!visible.length && <div className="wf-empty compact">No activity in this filter.</div>}</div></aside>;
}

function TimelineGraph({ workspace, selectedMultiverseId, selectedTickId, selectMultiverse, selectTick }: { workspace: WorkspacePayload; selectedMultiverseId: string | null; selectedTickId: string | null; selectMultiverse: (id: string) => void; selectTick: (multiverseId: string, tickId: string) => void }) {
  if (!workspace.multiverses.length) return <div className="wf-empty">No multiverses have been initialized.</div>;
  const sorted = [...workspace.multiverses].sort((a, b) => a.depth - b.depth || (a.fork_tick_index ?? -1) - (b.fork_tick_index ?? -1) || a.ui_label.localeCompare(b.ui_label, undefined, { numeric: true }));
  const renderedEdgeKeys = new Set(workspace.lineage_edges.map((edge) => `${edge.parent_multiverse_id}:${edge.child_multiverse_id}`));
  const displayEdges = [
    ...workspace.lineage_edges,
    ...sorted
      .filter((mv) => mv.parent_multiverse_id && !renderedEdgeKeys.has(`${mv.parent_multiverse_id}:${mv.id}`))
      .map((mv) => ({ parent_multiverse_id: mv.parent_multiverse_id!, child_multiverse_id: mv.id, id: `synthetic-${mv.id}` })),
  ];
  const rowHeight = 58;
  const startX = 112;
  const tickWidth = 58;
  const tickGap = 14;
  const positions = new Map<string, { x: number; y: number }>();
  sorted.forEach((item, index) => positions.set(item.id, { x: 22 + item.depth * 48, y: 34 + index * rowHeight }));
  const maxTicks = Math.max(...sorted.map((item) => (workspace.ticks_by_multiverse[item.id] || []).length), 1);
  const width = Math.max(860, startX + maxTicks * (tickWidth + tickGap) + 260);
  const height = Math.max(235, 74 + sorted.length * rowHeight);
  return <div className="wf-timeline-scroll"><div className="wf-timeline-canvas" style={{ width, height }}>{displayEdges.map((edge, index) => <TimelineEdge key={edge.id || index} edge={edge} positions={positions} startX={startX} />)}{sorted.map((mv, mvIndex) => { const pos = positions.get(mv.id)!; const ticks = workspace.ticks_by_multiverse[mv.id] || []; const selected = mv.id === selectedMultiverseId; const color = branchColor(mv.ui_label, mvIndex); const forkOffset = mv.fork_tick_index == null ? null : startX + Math.max(0, mv.fork_tick_index) * (tickWidth + tickGap) + tickWidth / 2; return <div key={mv.id} className={`wf-rail-row ${selected ? 'selected' : ''}`} style={{ top: pos.y, '--rail-color': color } as CSSProperties}><button className={`wf-rail-label ${selected ? 'selected' : ''}`} style={{ left: pos.x }} onClick={() => selectMultiverse(mv.id)}><i /><strong>{mv.ui_label}</strong><span>{mv.status}</span></button><span className="wf-rail-line" style={{ left: startX, width: Math.max(80, ticks.length * (tickWidth + tickGap) - tickGap) }} />{forkOffset != null && <span className="wf-fork-marker" style={{ left: forkOffset }} title={`Fork point T${mv.fork_tick_index}`} />} {ticks.map((tick, index) => <button key={tick.id} className={`wf-tick-box ${tick.id === selectedTickId ? 'active' : ''} ${statusClass(tick.status)}`} style={{ left: startX + index * (tickWidth + tickGap) }} onClick={() => selectTick(mv.id, tick.id)}><i /><strong>{tick.ui_label || `T${tick.tick_index}`}</strong><span>{countBundle(tick, ['events', 'executed_events'])}e · {countBundle(tick, ['social_posts', 'social_media_logs'])}p</span></button>)}{!ticks.length && <span className="wf-no-ticks" style={{ left: startX }}>No ticks yet</span>}<div className="wf-rail-name" style={{ left: startX + Math.max(1, ticks.length) * (tickWidth + tickGap) + 18 }}><strong>{mv.ui_label}</strong><span>{firstWords(mv.branch_reason || (mv.parent_multiverse_id ? 'Branch path' : 'Root timeline'), 7)}</span></div></div>; })}</div></div>;
}

function TimelineEdge({ edge, positions, startX }: { edge: any; positions: Map<string, { x: number; y: number }>; startX: number }) {
  const parent = positions.get(edge.parent_multiverse_id);
  const child = positions.get(edge.child_multiverse_id);
  if (!parent || !child) return null;
  const x1 = startX - 28;
  const y1 = parent.y + 16;
  const x2 = startX - 2;
  const y2 = child.y + 16;
  return <svg className="wf-lineage-svg" style={{ left: 0, top: 0 }} width="100%" height="100%"><path d={`M ${x1} ${y1} C ${x1 + 18} ${y1}, ${x2 - 18} ${y2}, ${x2} ${y2}`} stroke="#9aa0a6" strokeWidth="1.5" fill="none" strokeLinecap="round" /></svg>;
}

function TickOverview({ tick, workspace, inspector }: { tick?: TickSnapshot; workspace: WorkspacePayload; inspector: InspectorState }) {
  const [tab, setTab] = useState<TickDetailTab>('overview');
  useEffect(() => setTab('overview'), [tick?.id]);
  const inspected = inspectedTickPayload(inspector, tick);
  const events = tickCollection(tick, inspected, ['events'], ['events', 'executed_events', 'queued_events']);
  const social = tickCollection(tick, inspected, ['social_posts', 'oasis_actions'], ['social_posts', 'social_media_logs', 'oasis_actions', 'oasis_action_logs', 'social_actions']);
  const tools = tickCollection(tick, inspected, ['tool_calls'], ['tool_calls', 'tool_call_logs']);
  const emotion = tickCollection(tick, inspected, ['emotion_snapshots'], ['emotion_observability_after_god_review', 'emotion_observability', 'emotion_self_ratings']);
  const graphs = tickCollection(tick, inspected, ['graph_snapshots', 'sociology_signals'], ['graph_snapshots', 'graphs', 'sociology_result']);
  const oasis = tickCollection(tick, inspected, ['oasis_actions'], ['oasis_actions', 'oasis_action_logs']).length;
  const tabs = [
    ['overview', 'Overview', null],
    ['events', 'Events', events.length],
    ['social', 'Social', social.length],
    ['tools', 'Tool Calls', tools.length],
    ['emotion', 'Emotion', emotion.length],
    ['graphs', 'Graphs', graphs.length],
    ['raw', 'Raw', null],
  ] as Array<[TickDetailTab, string, number | null]>;
  return <section className="wf-card wf-tick-detail"><div className="wf-tick-detail-head"><strong>{tick?.ui_label || 'No tick selected'}</strong><span>{tick?.summary ? firstWords(tick.summary, 18) : 'Click a tick to inspect its bundle.'}</span></div><div className="wf-tick-tabs" role="tablist">{tabs.map(([key, label, count]) => <button key={key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)} role="tab" aria-selected={tab === key}>{label}{count == null ? '' : ` ${count}`}</button>)}</div><div className="wf-tick-tab-panel">{tab === 'overview' && <div className="wf-metric-grid"><Metric title="Tick Summary" value={tick ? firstWords(tick.summary, 24) : 'No tick selected'} meta={tick?.ui_label || 'none'} /><Metric title="Event Breakdown" value={`${events.length} events`} meta={`${social.length} social · ${oasis} OASIS`} /><Metric title="Emotion Snapshot" value={emotionSummary(emotion, workspace)} meta={inspected ? 'inspected collection' : 'workspace/bundle fallback'} /><Metric title="God Agent" value={String(inspected?.god_review?.decision || tick?.final_bundle?.god_review?.decision || tick?.final_bundle?.god_agent?.decision || 'not reviewed')} meta="end-of-tick decision" /></div>}{tab === 'events' && <><EventDigest items={events} /><CollectionPanel items={events} empty="No inspected or bundled events for this tick." /></>}{tab === 'social' && <><SocialInteractionGraph items={social} workspace={workspace} /><CollectionPanel items={social} empty="No inspected social posts or OASIS actions for this tick." /></>}{tab === 'tools' && <CollectionPanel items={tools} empty="No inspected tool calls for this tick." />}{tab === 'emotion' && <><EmotionPanel items={emotion} workspace={workspace} /><CollectionPanel items={emotion} empty="No inspected emotion snapshots for this tick." /></>}{tab === 'graphs' && <><DependencyGraphPanel items={graphs} workspace={workspace} /><GraphSnapshotDigest items={graphs} /></>}{tab === 'raw' && <details className="wf-raw"><summary>Tick debug payload</summary><pre>{JSON.stringify({ tick, inspected }, null, 2)}</pre></details>}</div></section>;
}

function CollectionPanel({ items, empty }: { items: any[]; empty: string }) {
  return <div className="wf-collection-list">{items.length ? items.slice(0, 24).map((item, index) => <article className="wf-collection-row" key={collectionKey(item, index)}><div><strong>{collectionTitle(item, index)}</strong><p>{collectionBody(item)}</p></div><span>{collectionMeta(item)}</span></article>) : <div className="wf-empty compact">{empty}</div>}</div>;
}

function EventDigest({ items }: { items: any[] }) {
  if (!items.length) return <div className="wf-visual-empty">No event records for this tick yet.</div>;
  return <section className="wf-event-digest">{items.slice(0, 6).map((item, index) => <article key={collectionKey(item, index)}><strong>{collectionTitle(item, index)}</strong><p>{collectionBody(item)}</p><span>{collectionMeta(item)}</span></article>)}</section>;
}

function SocialInteractionGraph({ items, workspace }: { items: any[]; workspace: WorkspacePayload }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const graph = socialGraph(items, workspace, labels);
  const selected = graph.nodes.find((node) => node.id === selectedId) || graph.nodes[0];
  if (!graph.edges.length) return <div className="wf-visual-empty">No actor-to-channel social graph for this tick yet.</div>;
  return <section className="wf-visual-panel"><div className="wf-visual-head"><strong>Social interaction graph</strong><span>{plural(graph.nodes.length, 'node')} · {plural(graph.edges.length, 'edge')} · editable labels</span></div><div className="wf-directed-graph"><svg viewBox="0 0 760 310" role="img" aria-label="Directed social interaction graph"><defs><marker id="arrow-social" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#1a73e8" /></marker></defs>{graph.edges.map((edge) => <line key={edge.id} x1={edge.x1} y1={edge.y1} x2={edge.x2} y2={edge.y2} stroke="#1a73e8" strokeWidth="2" markerEnd="url(#arrow-social)" opacity=".72" />)}{graph.nodes.map((node) => <g key={node.id} className={node.id === selected?.id ? 'selected' : ''} onClick={() => setSelectedId(node.id)}><circle cx={node.x} cy={node.y} r={node.kind === 'channel' ? 42 : 34} fill={node.kind === 'channel' ? '#e8f0fe' : '#fff'} stroke={node.id === selected?.id ? '#1a73e8' : '#dadce0'} strokeWidth={node.id === selected?.id ? 3 : 1.5} /><text x={node.x} y={node.y - 3} textAnchor="middle" fontSize="12" fontWeight="700" fill="#202124">{firstWords(node.label, 3)}</text><text x={node.x} y={node.y + 14} textAnchor="middle" fontSize="10" fill="#5f6368">{node.kind}</text></g>)}</svg><aside className="wf-graph-editor"><strong>{selected?.label || 'Select a node'}</strong><span>{selected?.kind || 'node'}</span>{selected && <input className="wf-input" value={labels[selected.id] || selected.label} onChange={(event) => setLabels((current) => ({ ...current, [selected.id]: event.target.value }))} aria-label="Edit node label" />}<p>{selected?.meta || 'Click a graph node to inspect or rename it locally.'}</p></aside></div></section>;
}

function EmotionPanel({ items, workspace }: { items: any[]; workspace: WorkspacePayload }) {
  const rows = items.length ? items.slice(0, 8).map((item, index) => ({ label: collectionTitle(item, index), value: numericSignal(item), meta: collectionBody(item) })) : workspace.emotion_observability.emotions_seen.slice(0, 8).map((emotion) => ({ label: emotion, value: 0.35, meta: 'observed in workspace' }));
  if (!rows.length) return <div className="wf-visual-empty">No emotion vectors available yet.</div>;
  return <section className="wf-visual-panel"><div className="wf-visual-head"><strong>Emotion vector</strong><span>{plural(rows.length, 'signal')}</span></div><div className="wf-emotion-bars">{rows.map((row) => <div className="wf-emotion-bar" key={row.label}><span>{row.label}</span><b><i style={{ width: `${Math.max(8, Math.min(100, row.value * 100))}%` }} /></b><small>{firstWords(row.meta, 10)}</small></div>)}</div></section>;
}

function DependencyGraphPanel({ items, workspace }: { items: any[]; workspace: WorkspacePayload }) {
  const rows = dependencyRowsFromSnapshots(items, workspace);
  if (!rows.length) return <div className="wf-visual-empty">No dependency or influence edges available yet.</div>;
  return <section className="wf-visual-panel"><div className="wf-visual-head"><strong>Dependency / influence graph</strong><span>{plural(rows.length, 'edge')}</span></div><div className="wf-dependency-graph">{rows.map((row: any, index: number) => <div className="wf-dependency-edge" key={`${row.layer}-${row.source}-${row.target}-${index}`}><span>{humanLayer(row.layer)}</span><b>{row.source} → {row.target}</b><small>{row.reason}</small><i style={{ width: `${Math.max(10, Math.min(100, Math.abs(Number(row.weight || 0.4)) * 100))}%` }} /></div>)}</div></section>;
}

function GraphSnapshotDigest({ items }: { items: any[] }) {
  const snapshots = items.filter((item) => item?.graph?.summary || item?.graph?.nodes || item?.graph?.edges);
  if (!snapshots.length) return <div className="wf-empty compact">No graph snapshots for this tick.</div>;
  return <section className="wf-graph-digest">{snapshots.slice(0, 8).map((snapshot, index) => {
    const summary = snapshot.graph?.summary || {};
    return <article key={collectionKey(snapshot, index)}><strong>{humanLayer(snapshot.layer || snapshot.graph?.layer || `Layer ${index + 1}`)}</strong><p>{summary.interpretation || `${summary.edge_count ?? 0} edges · ${summary.average_weight == null ? 'unknown' : Number(summary.average_weight).toFixed(2)} average weight`}</p><span>{snapshot.tick_index == null ? 'snapshot' : `T${snapshot.tick_index}`} · {summary.edge_count ?? snapshot.graph?.edges?.length ?? 0} edges</span></article>;
  })}</section>;
}

function inspectedTickPayload(inspector: InspectorState, tick?: TickSnapshot): any | null {
  if (!tick || inspector?.type !== 'tick') return null;
  const item = inspector.payload?.item || inspector.payload;
  return item?.id === tick.id ? inspector.payload : null;
}

function tickCollection(tick: TickSnapshot | undefined, inspected: any | null, inspectedKeys: string[], bundleKeys: string[]): any[] {
  const inspectedItems = inspectedKeys.flatMap((key) => normalizeCollection(inspected?.[key]));
  if (inspectedItems.length) return inspectedItems;
  return bundleKeys.flatMap((key) => normalizeCollection(bundleValue(tick, [key])));
}

function normalizeCollection(value: unknown): any[] {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  if (typeof value === 'object') return Object.entries(value as Record<string, unknown>).map(([key, nested]) => typeof nested === 'object' && nested != null ? { key, ...(nested as Record<string, unknown>) } : { key, value: nested });
  return [{ value }];
}

function collectionKey(item: any, index: number): string {
  return String(item?.id || item?.key || item?.title || item?.tool_name || item?.emotion || item?.layer || index);
}

function collectionTitle(item: any, index: number): string {
  return String(item?.title || item?.name || item?.tool_name || item?.function_name || item?.emotion || item?.layer || item?.model || item?.event_type || item?.action_type || item?.payload?.action_type || item?.meta?.action?.action_type || item?.channel || item?.platform || item?.actor_name || item?.key || `Record ${index + 1}`);
}

function collectionBody(item: any): string {
  return firstWords(item?.description || item?.summary || socialBody(item) || item?.message || item?.rationale || item?.expected_impact || item?.actual_impact?.summary || item?.result?.status || item?.arguments_summary || item?.tool_input_summary || item?.value || readableObject(item), 34);
}

function collectionMeta(item: any): string {
  const parts = [item?.status, item?.event_type || actionTypeOf(item), item?.channel || item?.payload?.channel, item?.created_at && fmtDate(item.created_at)].filter(Boolean);
  return parts.length ? parts.join(' · ') : 'record';
}

function numericSignal(item: any): number {
  const raw = item?.intensity ?? item?.score ?? item?.weight ?? item?.magnitude ?? item?.value;
  const parsed = typeof raw === 'number' ? raw : Number(raw);
  return Number.isFinite(parsed) ? Math.max(0, Math.min(1, Math.abs(parsed))) : 0.45;
}

function readableObject(item: any): string {
  if (!item || typeof item !== 'object') return String(item ?? '');
  return Object.entries(item)
    .filter(([key, value]) => value != null && typeof value !== 'object' && !isMetadataField(key))
    .slice(0, 6)
    .map(([key, value]) => `${key.replaceAll('_', ' ')}: ${value}`)
    .join(' · ') || 'Structured record';
}

function dependencyRowsFromSnapshots(items: any[], workspace: WorkspacePayload) {
  const rows: Array<{ layer: string; source: string; target: string; reason: string; weight: number }> = [];
  const workspaceActorNames = new Map((workspace.actors || []).map((actor: any) => [String(actor.id), actor.name || shortId(actor.id)]));
  for (const snapshot of items) {
    const graph = snapshot?.graph;
    if (!graph || !Array.isArray(graph.edges)) continue;
    const graphActorNames = new Map<string, string>();
    for (const node of Array.isArray(graph.nodes) ? graph.nodes : []) {
      if (node?.actor_id) graphActorNames.set(String(node.actor_id), node.name || shortId(node.actor_id));
    }
    for (const edge of graph.edges) {
      const layer = edge.layer || snapshot.layer || graph.layer || 'influence';
      const source = edge.source || graphActorNames.get(String(edge.source_actor_id)) || workspaceActorNames.get(String(edge.source_actor_id)) || 'Public system';
      const target = edge.target || graphActorNames.get(String(edge.target_actor_id)) || workspaceActorNames.get(String(edge.target_actor_id)) || nullTargetLabel(layer);
      rows.push({
        layer,
        source,
        target,
        reason: edge.reason || edge.evidence?.summary || graph.summary?.interpretation || 'Derived from tick events, social activity, and graph pressure.',
        weight: Number(edge.weight ?? graph.summary?.average_weight ?? 0.4),
      });
    }
  }
  if (rows.length) return dedupeDependencyRows(rows).slice(0, 10);
  const strongest = workspace.graphs.influence_summary?.strongest_edges || [];
  return strongest.slice(0, 8).map((edge: any) => ({
    layer: edge.layer || 'influence',
    source: workspaceActorNames.get(String(edge.source_actor_id)) || 'Public system',
    target: workspaceActorNames.get(String(edge.target_actor_id)) || nullTargetLabel(edge.layer),
    reason: edge.confidence ? `Confidence ${edge.confidence}` : 'Workspace-level influence edge.',
    weight: Number(edge.weight || 0.4),
  }));
}

function dedupeDependencyRows(rows: Array<{ layer: string; source: string; target: string; reason: string; weight: number }>) {
  const seen = new Set<string>();
  return rows.filter((row) => {
    const key = `${row.layer}:${row.source}:${row.target}:${row.reason}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function nullTargetLabel(layer?: string): string {
  const key = String(layer || '').toLowerCase();
  if (key.includes('exposure')) return 'Public attention';
  if (key.includes('agenda')) return 'Public agenda';
  if (key.includes('emotion')) return 'Public emotion';
  return 'Information environment';
}

function humanLayer(layer?: string): string {
  return String(layer || 'Influence').replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

function socialGraph(items: any[], workspace: WorkspacePayload, labels: Record<string, string>) {
  const actorNames = new Map((workspace.actors || []).map((actor: any) => [String(actor.id), actor.name || shortId(actor.id)]));
  const nodes = new Map<string, { id: string; label: string; kind: string; meta: string; x: number; y: number }>();
  const edges: Array<{ id: string; x1: number; y1: number; x2: number; y2: number }> = [];
  const channelId = 'channel:OASIS';
  nodes.set(channelId, { id: channelId, label: labels[channelId] || 'OASIS channel', kind: 'channel', meta: 'Shared public channel for social observations.', x: 380, y: 155 });
  const semantic = items.filter((item) => actorIdOf(item) || socialBody(item));
  semantic.slice(0, 10).forEach((item, index) => {
    const actorId = actorIdOf(item) || `unknown:${index}`;
    const nodeId = `actor:${actorId}`;
    const angle = -Math.PI / 2 + (index / Math.max(1, semantic.length)) * Math.PI * 2;
    const x = 380 + Math.cos(angle) * 250;
    const y = 155 + Math.sin(angle) * 105;
    const action = actionTypeOf(item);
    nodes.set(nodeId, {
      id: nodeId,
      label: labels[nodeId] || actorNames.get(String(actorId)) || `Actor ${shortId(actorId)}`,
      kind: action || 'actor',
      meta: firstWords(socialBody(item) || collectionBody(item), 18),
      x,
      y,
    });
    edges.push({ id: collectionKey(item, index), x1: x, y1: y, x2: 344 + Math.cos(angle) * 26, y2: 155 + Math.sin(angle) * 26 });
  });
  return { nodes: [...nodes.values()], edges };
}

function actorIdOf(item: any): string | null {
  return item?.actor_id || item?.payload?.actor_id || item?.meta?.action?.actor_id || null;
}

function actionTypeOf(item: any): string {
  return String(item?.action_type || item?.payload?.action_type || item?.meta?.action?.action_type || item?.channel || 'social');
}

function socialBody(item: any): string {
  return String(item?.body || item?.payload?.body || item?.meta?.action?.body || item?.content || item?.text || '');
}

function isMetadataField(key: string): boolean {
  const normalized = key.toLowerCase().trim().replace(/[\s-]+/g, '_');
  return normalized === 'id'
    || normalized.endsWith('_id')
    || normalized.includes('revision')
    || normalized.includes('snapshot')
    || normalized.includes('idempotency')
    || normalized === 'updated_at';
}

function emotionSummary(items: any[], workspace: WorkspacePayload): string {
  const labels = items.map((item) => item?.emotion || item?.key || item?.source).filter(Boolean);
  return labels.slice(0, 3).join(', ') || workspace.emotion_observability.emotions_seen.slice(0, 3).join(', ') || 'No emotion signal yet';
}

function SignalGrid({ workspace }: { workspace: WorkspacePayload }) {
  const influence = workspace.graphs.influence_summary || {};
  const traitRows = (workspace.graphs.trait_vectors || []).map((item: any) => ({ title: String(item.name || item.entity_id || 'trait vector'), meta: traitMeta(item.trait_vector || item) }));
  const influenceRows = Object.entries(influence.layer_counts || {}).map(([layer, count]) => ({ title: layer, meta: `${count} graph edges` }));
  return <section className="wf-signal-grid"><SignalCard title="Graph Layers" icon="layers" rows={workspace.graphs.layers.map((layer) => ({ title: layer.layer, meta: `${layer.count} snapshots · latest ${layer.latest_tick_index == null ? 'n/a' : `T${layer.latest_tick_index}`}` }))} /><SignalCard title="Graph Influence" icon="target" rows={[...influenceRows, { title: 'Fallback edges', meta: String(influence.fallback_edge_count || 0) }]} /><SignalCard title="Trait Vectors" icon="users" rows={traitRows} /><SignalCard title="Emotion Observability" icon="activity" rows={workspace.emotion_observability.emotions_seen.map((emotion) => ({ title: emotion, meta: 'observed' }))} /><SignalCard title="Sociology Signals" icon="sociology" rows={[...workspace.sociology.models_seen.map((model) => ({ title: model, meta: 'model seen' })), { title: 'Prompt influences', meta: `${workspace.sociology.prompt_influences?.length || 0} rows` }]} /><SignalCard title="Reports / Jobs" icon="file" rows={[{ title: `${workspace.reports.length} reports`, meta: 'generated reports' }, { title: `${workspace.jobs.length} jobs`, meta: 'background jobs' }]} /></section>;
}

function SignalCard({ title, icon, rows }: { title: string; icon: IconName; rows: Array<{ title: string; meta: string }> }) {
  return <article className="wf-card wf-signal-card"><h3><Icon name={icon} size={16} />{title}</h3>{rows.length ? rows.slice(0, 8).map((row) => <div className="wf-signal-row" key={`${title}-${row.title}`}><strong>{row.title}</strong><span>{row.meta}</span></div>) : <div className="wf-empty compact">No signal yet.</div>}</article>;
}

function InspectorPanel({ workspace, selectedMv, selectedTick, inspector, inspect, selectTick, simulateNextTick, busy }: { workspace: WorkspacePayload; selectedMv?: Multiverse; selectedTick?: TickSnapshot; inspector: InspectorState; inspect: (type: string, id: string) => void; selectTick: (multiverseId: string, tickId: string) => void; simulateNextTick: () => void; busy: boolean }) {
  const item = inspector?.payload?.item || inspector?.payload || selectedTick || selectedMv || workspace.big_bang;
  const inspected = inspectedTickPayload(inspector, selectedTick);
  const inspectedEvents = tickCollection(selectedTick, inspected, ['events'], ['events', 'executed_events', 'queued_events']);
  const collections = Object.entries(inspector?.payload || {}).filter(([, value]) => Array.isArray(value) && value.length) as Array<[string, any[]]>;
  return <aside className="wf-inspector"><div className="wf-inspector-head"><div><Icon name="sparkle" size={16} color="#1a73e8" /><strong>Inspector</strong></div><Icon name="chevronUp" size={16} /></div><section className="wf-selected-card"><span>Selected</span><h2>{selectedTick?.ui_label || selectedMv?.ui_label || workspace.big_bang.name}</h2><p>{selectedTick ? firstWords(selectedTick.summary, 18) : firstWords(selectedMv?.branch_reason || workspace.big_bang.description || 'Workspace summary', 18)}</p><Sparkline values={selectedSparkValues(selectedTick, workspace)} width={260} height={40} color="#1a73e8" /></section><ConfigCard title="Selection details" rows={[["Type", inspector?.type || (selectedTick ? 'tick' : 'multiverse')], ["Status", item.status || item.decision || 'n/a'], ["Created", fmtDate(item.created_at)], ["Current tick", selectedTick?.ui_label || 'none']]} /><InspectorReadable item={item} collections={collections} /><section className="wf-card wf-recent-card"><h3>{inspectedEvents.length ? 'Inspected Events' : 'Recent Ticks'}</h3>{inspectedEvents.length ? inspectedEvents.slice(0, 5).map((event, index) => <article key={collectionKey(event, index)} className="wf-recent-event"><strong>{collectionTitle(event, index)}</strong><span>{collectionBody(event)}</span><small>{collectionMeta(event)}</small></article>) : workspace.latest_ticks.slice(0, 5).map((tick) => <button key={tick.id} onClick={() => selectTick(tick.multiverse_id, tick.id)}><strong>{tick.ui_label}</strong><span>{firstWords(tick.summary, 10)}</span></button>)}</section><section className="wf-card wf-reasoning-card"><h3><Icon name="sparkle" size={14} color="#1a73e8" />Next action</h3><ul><li>Step selected timeline runs one tick immediately for the selected path.</li><li>Run 12 ticks creates a job and now auto-runs with a local fallback if Redis is unavailable.</li><li>Raw payload remains behind explicit debug disclosure.</li></ul><button className="wf-btn wf-btn--text" disabled={busy || statusClass(workspace.big_bang.status) === 'paused'} title={statusClass(workspace.big_bang.status) === 'paused' ? 'Resume the simulation before stepping.' : 'Run one immediate tick for the selected timeline.'} onClick={simulateNextTick}>Step selected timeline →</button></section>{collections.slice(0, 4).map(([key, value]) => <ConfigCard key={key} title={key.replaceAll('_', ' ')} rows={[["Items", value.length], ["First", value[0] ? collectionTitle(value[0], 0) : 'none']]} />)}<details className="wf-raw"><summary>Raw API payload</summary><pre>{JSON.stringify(inspector?.payload || { item }, null, 2)}</pre></details></aside>;
}

function InspectorReadable({ item, collections }: { item: any; collections: Array<[string, any[]]> }) {
  const isBigBang = !!item?.scenario_input || item?.current_config_version != null;
  if (isBigBang) return null;
  const summary = collectionBody(item);
  const status = item?.status || item?.decision || item?.report_status;
  const label = item?.ui_label || item?.title || item?.report_type || item?.job_type;
  const parsedCollections = collections.filter(([, value]) => value.length).slice(0, 3);
  if (!summary && !label && !status && !parsedCollections.length) return null;
  return <section className="wf-card wf-inspector-readable wf-readable-summary"><h3>{item?.tick_index != null ? 'Tick summary' : 'Selection summary'}</h3>{summary && <p>{summary}</p>}<div className="wf-readable-chips">{label && <Chip tone="blue">{String(label)}</Chip>}{status && <Chip tone="green">{String(status)}</Chip>}</div>{parsedCollections.map(([key, value]) => <div className="wf-inspector-collection" key={key}><strong>{key.replaceAll('_', ' ')}</strong><span>{value.length} parsed records</span></div>)}</section>;
}

function Metric({ title, value, meta }: { title: string; value: string; meta: string }) { return <article className="wf-metric"><h3>{title}</h3><strong>{value}</strong><span>{meta}</span></article>; }
function Chip({ children, tone }: { children: ReactNode; tone?: string }) { return <span className={`wf-chip ${tone ? `wf-chip--${tone}` : ''}`}><i />{children}</span>; }
function Pill({ status }: { status: string }) { const key = statusClass(status); return <span className={`wf-pill wf-pill--${key}`}><i />{status}</span>; }
function Toast({ message }: { message: string }) { return <div className={`wf-toast ${message ? 'visible' : ''}`} role="status" aria-live="polite">{message}</div>; }

function latestTime(workspace?: WorkspacePayload | null): string {
  const tick = workspace?.latest_ticks[0];
  if (!tick) return 'T0';
  return tick.ui_label || `T${tick.tick_index}`;
}

function bundleValue(tick: TickSnapshot | undefined, keys: string[]): any {
  if (!tick) return undefined;
  const bundles = [tick.final_bundle || {}, tick.provisional_bundle || {}];
  for (const bundle of bundles) for (const key of keys) if (bundle[key] != null) return bundle[key];
  return undefined;
}

function countBundle(tick: TickSnapshot | undefined, keys: string[]): number {
  const value = bundleValue(tick, keys);
  if (Array.isArray(value)) return value.length;
  if (typeof value === 'number') return value;
  if (value && typeof value === 'object') return Object.keys(value).length;
  return 0;
}

function selectedSparkValues(tick: TickSnapshot | undefined, workspace: WorkspacePayload): number[] {
  const base = workspace.latest_ticks.slice(-8).map((item) => countBundle(item, ['events', 'executed_events']) + countBundle(item, ['social_posts', 'social_media_logs']) + 1);
  if (base.length >= 2) return base;
  const current = countBundle(tick, ['events', 'executed_events']) + 1;
  return [1, 2, current, current + 1, Math.max(2, current - 1), current + 2];
}

function branchColor(label: string, index: number): string {
  const palette = ['#1a73e8', '#34a853', '#8430ce', '#f9ab00', '#ea4335', '#00acc1', '#e8710a'];
  const seed = Array.from(label || String(index)).reduce((sum, char) => sum + char.charCodeAt(0), index);
  return palette[Math.abs(seed) % palette.length];
}

function shortId(id: unknown): string {
  return id == null || id === '' ? 'n/a' : compactId(String(id));
}

function reportTitle(report: any): string {
  return report.title || report.name || report.report_type || report.kind || 'Report';
}

function reportVersions(payload: any): any[] {
  const versions = payload?.versions || payload?.report_versions || payload?.report?.versions;
  if (Array.isArray(versions)) return versions;
  if (payload?.type === 'report_version' && payload?.item) return [payload.item];
  return [];
}

function reportVersionIdsFromJob(job: any): string[] {
  const result = job?.result || {};
  const ids = [
    result.report_version_id,
    result.final_report_version_id,
    ...(Array.isArray(result.report_version_ids) ? result.report_version_ids : []),
  ].filter(Boolean).map(String);
  return [...new Set(ids)];
}

function artifactChip(label: string, artifactId: unknown): ReactNode {
  if (!artifactId) return <span className="wf-artifact-chip muted">{label}: none</span>;
  const id = String(artifactId);
  return <a className="wf-artifact-chip" href={`/api/artifacts/${encodeURIComponent(id)}`} target="_blank" rel="noreferrer">{label}: {shortId(id)}</a>;
}

function payloadSummary(payload: unknown): string {
  if (!payload) return 'No payload summary.';
  if (typeof payload === 'string') return firstWords(payload, 24);
  if (typeof payload === 'object') {
    const keys = Object.keys(payload as Record<string, unknown>);
    return keys.length ? `Payload: ${keys.slice(0, 6).join(', ')}` : 'Empty payload object.';
  }
  return String(payload);
}

function jobSummary(job: any): string {
  if (job?.error) return firstWords(job.error, 24);
  const result = job?.result || {};
  const progress = result.progress || {};
  const parts = [
    result.ticks_run != null ? `${result.ticks_run} ticks run` : '',
    result.latest_tick_label ? `latest ${result.latest_tick_label}` : '',
    result.multiverse_count != null ? `${result.multiverse_count} multiverses` : '',
    result.stopped_reason ? `stopped: ${result.stopped_reason}` : '',
    progress.percent != null ? `${progress.percent}%` : '',
  ].filter(Boolean);
  return parts.length ? parts.join(' · ') : payloadSummary(job?.payload);
}

function jobDisplayName(jobType: unknown): string {
  const type = String(jobType || '');
  const labels: Record<string, string> = {
    run_big_bang_until_complete: 'Run simulation',
    run_multiverse_tick: 'Step timeline',
    simulate_multiverse_ticks: 'Run timeline ticks',
    generate_multiverse_report: 'Generate timeline report',
    generate_final_big_bang_report: 'Generate final report',
    initialize_big_bang: 'Initialize simulation',
  };
  return labels[type] || type.replaceAll('_', ' ') || 'Job';
}

function traitMeta(vector: any): string {
  if (!vector || typeof vector !== 'object') return 'no trait metadata';
  const keys = ['trustworthiness', 'secrecy', 'reputation', 'tendency', 'graph_influence', 'influence'];
  const parts = keys
    .filter((key) => vector[key] != null)
    .map((key) => `${key}: ${typeof vector[key] === 'object' ? JSON.stringify(vector[key]).slice(0, 28) : vector[key]}`);
  return parts.slice(0, 3).join(' · ') || `traits: ${Object.keys(vector).slice(0, 4).join(', ')}`;
}
