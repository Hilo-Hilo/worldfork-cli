const NAV_ITEMS = Object.freeze([
  { label: "Start Simulation", target: "start" },
  { label: "Select Big Bang", target: "big-bangs" },
  { label: "Timeline Preview", target: "preview" },
  { label: "Reports", target: "reports" },
]);

const HERO_NOTES = Object.freeze([
  {
    title: "Big Bang",
    body: "One root scenario owns the workspace, source-of-truth snapshot, actors, timelines, and reports.",
  },
  {
    title: "Recursive branches",
    body: "Every tick can fork into inspectable child multiverses with human-readable labels like M1.1:T7.",
  },
  {
    title: "Progressive detail",
    body: "Start with the essential path, then open events, sociology signals, graph changes, and reports.",
  },
]);

const PREVIEW_NODES = Object.freeze([
  {
    className: "wf-branch-node--root",
    label: "M1:T0",
    text: "A civic crisis enters the first tick.",
  },
  {
    className: "wf-branch-node--steady",
    label: "M1.1:T7",
    text: "Trust stabilizes; public silence softens.",
  },
  {
    className: "wf-branch-node--rupture",
    label: "M1.2:T7",
    text: "Coalitions split; attention spikes.",
  },
]);

const PREVIEW_SIGNALS = Object.freeze([
  { label: "emotion graph", value: "observed" },
  { label: "god agent", value: "reviewing" },
  { label: "reports", value: "per branch" },
]);

function el(tagName, className, text) {
  const node = document.createElement(tagName);

  if (className) {
    node.className = className;
  }

  if (text) {
    node.textContent = text;
  }

  return node;
}

function setNavigationTarget(node, target) {
  node.dataset.wfNavigate = target;
  node.type = "button";
  return node;
}

export function getLandingNavItems() {
  return NAV_ITEMS.map((item) => ({ ...item }));
}

export function createTopNav(options = {}) {
  const navItems = options.navItems || NAV_ITEMS;
  const nav = el("nav", "wf-topnav");
  nav.setAttribute("aria-label", "WorldFork primary navigation");

  const brand = el("div", "wf-topnav__brand");
  brand.append(el("span", "wf-topnav__mark", "W"));
  brand.append(el("span", "", "WorldFork"));

  const links = el("div", "wf-topnav__links");

  navItems.forEach((item) => {
    const link = setNavigationTarget(el("button", "wf-topnav__link", item.label), item.target);
    links.append(link);
  });

  const cta = setNavigationTarget(el("button", "wf-topnav__cta", "Start"), "start");

  nav.append(brand, links, cta);
  return nav;
}

export function createLandingHero() {
  const section = el("section", "wf-hero");

  const copy = el("div", "wf-hero__copy");
  copy.append(el("p", "wf-hero__eyebrow", "Personal simulation workbench"));

  const title = el("h1", "wf-hero__title");
  title.append("Fork one scenario into ");
  title.append(el("span", "", "many social futures"));
  title.append(".");

  copy.append(title);
  copy.append(
    el(
      "p",
      "wf-hero__lede",
      "Create a Big Bang, watch multiverse timelines branch over ticks, and inspect the sociology, graph shifts, emotion observations, and reports behind every path."
    )
  );

  const actions = el("div", "wf-hero__actions");
  actions.append(setNavigationTarget(el("button", "wf-hero__cta", "Start Simulation"), "start"));
  actions.append(setNavigationTarget(el("button", "wf-hero__secondary", "Preview Branching"), "preview"));
  copy.append(actions);

  const notes = el("div", "wf-hero__notes");
  HERO_NOTES.forEach((note) => {
    const card = el("article", "wf-hero__note");
    card.append(el("strong", "", note.title));
    card.append(el("span", "", note.body));
    notes.append(card);
  });
  copy.append(notes);

  section.append(copy, createBranchingPreview());
  return section;
}

export function createBranchingPreview() {
  const card = el("aside", "wf-branch-card");
  card.setAttribute("aria-label", "Branching timeline preview");

  const header = el("div", "wf-branch-card__header");
  const headerText = el("div");
  headerText.append(el("p", "wf-branch-card__kicker", "Live lineage"));
  headerText.append(el("h2", "wf-branch-card__title", "A timeline splits at T7"));
  header.append(headerText, el("span", "wf-branch-card__status", "God Agent gate"));

  const map = el("div", "wf-branch-map");
  PREVIEW_NODES.forEach((node) => {
    const branch = el("div", `wf-branch-node ${node.className}`);
    branch.append(el("span", "wf-branch-node__label", node.label));
    branch.append(el("span", "wf-branch-node__text", node.text));
    map.append(branch);
  });

  const signals = el("div", "wf-signal-strip");
  PREVIEW_SIGNALS.forEach((signal) => {
    const item = el("div", "wf-signal");
    item.append(el("span", "wf-signal__label", signal.label));
    item.append(el("span", "wf-signal__value", signal.value));
    signals.append(item);
  });

  card.append(header, map, signals);
  return card;
}

export function attachLandingNavigation(root, onNavigate) {
  if (!root) {
    return () => {};
  }

  const handleClick = (event) => {
    const trigger = event.target.closest("[data-wf-navigate]");

    if (!trigger || !root.contains(trigger)) {
      return;
    }

    const detail = {
      target: trigger.dataset.wfNavigate,
      label: trigger.textContent.trim(),
      trigger,
    };

    if (typeof onNavigate === "function") {
      onNavigate(detail);
    }

    root.dispatchEvent(
      new CustomEvent("worldfork:navigate", {
        bubbles: true,
        detail,
      })
    );
  };

  root.addEventListener("click", handleClick);
  return () => root.removeEventListener("click", handleClick);
}

export function renderLanding(root, options = {}) {
  if (!root) {
    return null;
  }

  const landing = el("main", "wf-landing");
  const shell = el("div", "wf-landing__shell");

  shell.append(createTopNav(options), createLandingHero(options));
  landing.append(shell);
  root.replaceChildren(landing);

  const detachNavigation = attachLandingNavigation(landing, options.onNavigate);

  return {
    element: landing,
    detachNavigation,
  };
}

const WorldForkLanding = Object.freeze({
  attachLandingNavigation,
  createBranchingPreview,
  createLandingHero,
  createTopNav,
  getLandingNavItems,
  renderLanding,
});

if (typeof window !== "undefined") {
  window.WorldForkLanding = WorldForkLanding;
}
