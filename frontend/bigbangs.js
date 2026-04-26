(function () {
  "use strict";

  const DEFAULT_ENDPOINTS = {
    bigBangs: "/api/big-bangs",
    scenarioBank: "/api/scenario-bank"
  };

  const STATUS_LABELS = {
    active: "Active",
    running: "Running",
    paused: "Paused",
    frozen: "Frozen",
    terminated: "Terminated",
    completed: "Completed",
    draft: "Draft",
    failed: "Failed",
    queued: "Queued"
  };

  const SORTERS = {
    updated_desc: (a, b) => dateValue(b.updatedAt) - dateValue(a.updatedAt),
    created_desc: (a, b) => dateValue(b.createdAt) - dateValue(a.createdAt),
    title_asc: (a, b) => a.title.localeCompare(b.title),
    status_asc: (a, b) => a.status.localeCompare(b.status)
  };

  function createBigBangSlice(options) {
    const config = Object.assign({
      root: null,
      endpoints: DEFAULT_ENDPOINTS,
      onSelectBigBang: null,
      onSelectScenario: null,
      fetcher: window.fetch.bind(window)
    }, options || {});

    config.endpoints = Object.assign({}, DEFAULT_ENDPOINTS, config.endpoints || {});

    const state = {
      bigBangs: [],
      scenarios: [],
      filteredBigBangs: [],
      filteredScenarios: [],
      filters: {
        query: "",
        status: "all",
        sort: "updated_desc"
      },
      loading: false,
      error: null
    };

    const root = resolveRoot(config.root);
    const refs = root ? collectRefs(root) : {};

    function setState(patch) {
      Object.assign(state, patch || {});
      state.filteredBigBangs = filterBigBangs(state.bigBangs, state.filters);
      state.filteredScenarios = filterScenarios(state.scenarios, state.filters.query);
      render();
      return state;
    }

    function render() {
      if (!root) return;

      if (refs.filters) {
        renderSearchFilterUI(refs.filters, {
          filters: state.filters,
          statuses: getAvailableStatuses(state.bigBangs),
          onChange: function (nextFilters) {
            setState({ filters: Object.assign({}, state.filters, nextFilters) });
          }
        });
      }

      if (refs.summary) {
        renderStatusSummaryCards(refs.summary, deriveStatusSummary(state.bigBangs));
      }

      if (refs.bigBangs) {
        renderBigBangCards(refs.bigBangs, state.filteredBigBangs, {
          loading: state.loading,
          error: state.error,
          onSelect: config.onSelectBigBang
        });
      }

      if (refs.scenarios) {
        renderScenarioBankCards(refs.scenarios, state.filteredScenarios, {
          loading: state.loading,
          error: state.error,
          onSelect: config.onSelectScenario
        });
      }
    }

    async function load() {
      setState({ loading: true, error: null });

      try {
        const results = await Promise.all([
          fetchJson(config.fetcher, config.endpoints.bigBangs),
          fetchJson(config.fetcher, config.endpoints.scenarioBank)
        ]);

        setState({
          bigBangs: unwrapCollection(results[0]).map(normalizeBigBang),
          scenarios: unwrapCollection(results[1]).map(normalizeScenario),
          loading: false,
          error: null
        });
      } catch (error) {
        setState({
          loading: false,
          error: error && error.message ? error.message : "Unable to load Big Bangs."
        });
      }

      return state;
    }

    render();

    return {
      state,
      load,
      render,
      setFilters: function (filters) {
        return setState({ filters: Object.assign({}, state.filters, filters || {}) });
      },
      setData: function (payload) {
        return setState({
          bigBangs: unwrapCollection(payload && payload.bigBangs).map(normalizeBigBang),
          scenarios: unwrapCollection(payload && payload.scenarios).map(normalizeScenario)
        });
      }
    };
  }

  async function fetchJson(fetcher, url) {
    if (!url) return [];

    const response = await fetcher(url, {
      headers: { "Accept": "application/json" }
    });

    if (!response.ok) {
      throw new Error("Request failed: " + response.status + " " + response.statusText);
    }

    return response.status === 204 ? [] : response.json();
  }

  function unwrapCollection(payload) {
    if (!payload) return [];
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload.items)) return payload.items;
    if (Array.isArray(payload.bigBangs)) return payload.bigBangs;
    if (Array.isArray(payload.scenarios)) return payload.scenarios;
    if (Array.isArray(payload.data)) return payload.data;
    return [];
  }

  function normalizeBigBang(item) {
    const scenario = item.scenario || item.scenario_input || {};
    const config = item.simulation_config || item.simulationConfig || {};
    const modelConfig = item.model_config || item.modelConfig || {};
    const title = item.title || item.name || scenario.title || item.label || "Untitled Big Bang";
    const status = normalizeStatus(item.status || item.state || item.lifecycle_status || "draft");

    return {
      id: item.id || item.big_bang_id || item.canonical_big_bang_id || "",
      title,
      description: item.description || scenario.description || scenario.prompt || item.prompt || "",
      status,
      statusLabel: STATUS_LABELS[status] || titleCase(status),
      createdAt: item.created_at || item.createdAt || "",
      updatedAt: item.updated_at || item.updatedAt || item.last_tick_at || "",
      timelineCount: numberFrom(item.timeline_count || item.timelineCount || item.multiverse_count || item.multiverseCount),
      activeTimelineCount: numberFrom(item.active_timeline_count || item.activeTimelineCount),
      terminatedTimelineCount: numberFrom(item.terminated_timeline_count || item.terminatedTimelineCount),
      tickCount: numberFrom(item.tick_count || item.tickCount || item.current_tick || item.currentTick),
      tickDuration: config.tick_duration || config.tickDuration || item.tick_duration || item.tickDuration || "",
      modelProvider: modelConfig.provider || item.model_provider || item.modelProvider || "",
      modelName: modelConfig.model || modelConfig.model_name || item.model_name || item.modelName || "",
      tags: normalizeTags(item.tags || scenario.tags),
      raw: item
    };
  }

  function normalizeScenario(item) {
    const title = item.title || item.name || item.label || "Untitled scenario";

    return {
      id: item.id || item.scenario_id || item.slug || title,
      title,
      description: item.description || item.prompt || item.summary || "",
      category: item.category || item.domain || item.type || "",
      tags: normalizeTags(item.tags),
      durationHint: item.duration_hint || item.durationHint || item.tick_duration || "",
      raw: item
    };
  }

  function deriveStatusSummary(bigBangs) {
    const summary = {
      total: bigBangs.length,
      active: 0,
      paused: 0,
      completed: 0,
      draft: 0,
      other: 0,
      timelines: 0,
      ticks: 0
    };

    bigBangs.forEach(function (bigBang) {
      if (bigBang.status === "active" || bigBang.status === "running") {
        summary.active += 1;
      } else if (bigBang.status === "paused" || bigBang.status === "frozen") {
        summary.paused += 1;
      } else if (bigBang.status === "completed" || bigBang.status === "terminated") {
        summary.completed += 1;
      } else if (bigBang.status === "draft" || bigBang.status === "queued") {
        summary.draft += 1;
      } else {
        summary.other += 1;
      }

      summary.timelines += bigBang.timelineCount || 0;
      summary.ticks += bigBang.tickCount || 0;
    });

    return [
      { label: "Big Bangs", value: summary.total, tone: "total" },
      { label: "Active", value: summary.active, tone: "active" },
      { label: "Paused or frozen", value: summary.paused, tone: "paused" },
      { label: "Completed", value: summary.completed, tone: "completed" },
      { label: "Drafts", value: summary.draft, tone: "draft" },
      { label: "Timelines", value: summary.timelines, tone: "timelines" },
      { label: "Ticks observed", value: summary.ticks, tone: "ticks" }
    ];
  }

  function renderSearchFilterUI(container, props) {
    const filters = props.filters;
    const statuses = props.statuses;
    const onChange = props.onChange || function () {};

    container.classList.add("wf-bb-filters");
    container.replaceChildren(
      element("label", { className: "wf-bb-search" }, [
        element("span", { text: "Search Big Bangs" }),
        element("input", {
          type: "search",
          value: filters.query,
          placeholder: "Scenario, tag, model, status...",
          oninput: function (event) {
            onChange({ query: event.target.value });
          }
        })
      ]),
      element("label", { className: "wf-bb-select" }, [
        element("span", { text: "Status" }),
        element("select", {
          value: filters.status,
          onchange: function (event) {
            onChange({ status: event.target.value });
          }
        }, [
          element("option", { value: "all", text: "All statuses" })
        ].concat(statuses.map(function (status) {
          return element("option", {
            value: status,
            text: STATUS_LABELS[status] || titleCase(status)
          });
        })))
      ]),
      element("label", { className: "wf-bb-select" }, [
        element("span", { text: "Sort" }),
        element("select", {
          value: filters.sort,
          onchange: function (event) {
            onChange({ sort: event.target.value });
          }
        }, [
          element("option", { value: "updated_desc", text: "Recently updated" }),
          element("option", { value: "created_desc", text: "Recently created" }),
          element("option", { value: "title_asc", text: "Scenario title" }),
          element("option", { value: "status_asc", text: "Status" })
        ])
      ])
    );
  }

  function renderStatusSummaryCards(container, summaryCards) {
    container.classList.add("wf-bb-summary-grid");
    container.replaceChildren.apply(container, summaryCards.map(function (card) {
      return element("article", { className: "wf-bb-summary-card is-" + card.tone }, [
        element("span", { className: "wf-bb-summary-label", text: card.label }),
        element("strong", { className: "wf-bb-summary-value", text: formatNumber(card.value) })
      ]);
    }));
  }

  function renderBigBangCards(container, bigBangs, options) {
    container.classList.add("wf-bb-card-grid");

    if (options && options.loading) {
      container.replaceChildren(emptyState("Loading Big Bangs...", "The scenario workspace list is being fetched."));
      return;
    }

    if (options && options.error) {
      container.replaceChildren(emptyState("Could not load Big Bangs", options.error));
      return;
    }

    if (!bigBangs.length) {
      container.replaceChildren(emptyState("No Big Bangs found", "Create or import a root scenario to begin exploring timelines."));
      return;
    }

    container.replaceChildren.apply(container, bigBangs.map(function (bigBang) {
      return bigBangCard(bigBang, options && options.onSelect);
    }));
  }

  function renderScenarioBankCards(container, scenarios, options) {
    container.classList.add("wf-bb-scenario-grid");

    if (options && options.loading) {
      container.replaceChildren(emptyState("Loading scenarios...", "Scenario bank entries are being fetched."));
      return;
    }

    if (options && options.error) {
      container.replaceChildren(emptyState("Could not load scenario bank", options.error));
      return;
    }

    if (!scenarios.length) {
      container.replaceChildren(emptyState("No scenario bank entries", "Add scenario templates through the API to show them here."));
      return;
    }

    container.replaceChildren.apply(container, scenarios.map(function (scenario) {
      return scenarioCard(scenario, options && options.onSelect);
    }));
  }

  function bigBangCard(bigBang, onSelect) {
    const meta = [
      bigBang.tickDuration && ["Tick", bigBang.tickDuration],
      bigBang.timelineCount !== null && ["Timelines", formatNumber(bigBang.timelineCount)],
      bigBang.tickCount !== null && ["Ticks", formatNumber(bigBang.tickCount)],
      bigBang.modelName && ["Model", bigBang.modelName]
    ].filter(Boolean);

    return element("article", {
      className: "wf-bb-card",
      dataset: { status: bigBang.status }
    }, [
      element("div", { className: "wf-bb-card-top" }, [
        element("span", { className: "wf-bb-pill", text: bigBang.statusLabel }),
        element("span", { className: "wf-bb-date", text: relativeOrDate(bigBang.updatedAt || bigBang.createdAt) })
      ]),
      element("h3", { text: bigBang.title }),
      element("p", {
        className: "wf-bb-description",
        text: bigBang.description || "No scenario description has been saved yet."
      }),
      element("dl", { className: "wf-bb-meta" }, meta.flatMap(function (pair) {
        return [
          element("dt", { text: pair[0] }),
          element("dd", { text: pair[1] })
        ];
      })),
      tagRow(bigBang.tags),
      element("button", {
        className: "wf-bb-action",
        type: "button",
        onclick: function () {
          if (typeof onSelect === "function") onSelect(bigBang);
          rootEvent("worldfork:bigbang-select", bigBang);
        },
        text: "Open workspace"
      })
    ]);
  }

  function scenarioCard(scenario, onSelect) {
    return element("article", { className: "wf-bb-scenario-card" }, [
      element("div", { className: "wf-bb-scenario-top" }, [
        element("span", { text: scenario.category || "Scenario" }),
        scenario.durationHint ? element("small", { text: scenario.durationHint }) : null
      ]),
      element("h3", { text: scenario.title }),
      element("p", {
        text: scenario.description || "No scenario description has been saved yet."
      }),
      tagRow(scenario.tags),
      element("button", {
        className: "wf-bb-secondary-action",
        type: "button",
        onclick: function () {
          if (typeof onSelect === "function") onSelect(scenario);
          rootEvent("worldfork:scenario-select", scenario);
        },
        text: "Use scenario"
      })
    ].filter(Boolean));
  }

  function tagRow(tags) {
    if (!tags.length) return element("div", { className: "wf-bb-tags is-empty" });

    return element("div", { className: "wf-bb-tags" }, tags.slice(0, 5).map(function (tag) {
      return element("span", { text: tag });
    }));
  }

  function emptyState(title, message) {
    return element("div", { className: "wf-bb-empty" }, [
      element("strong", { text: title }),
      element("p", { text: message })
    ]);
  }

  function filterBigBangs(bigBangs, filters) {
    const query = (filters.query || "").trim().toLowerCase();
    const status = filters.status || "all";
    const sorter = SORTERS[filters.sort] || SORTERS.updated_desc;

    return bigBangs.filter(function (bigBang) {
      if (status !== "all" && bigBang.status !== status) return false;
      if (!query) return true;

      return [
        bigBang.title,
        bigBang.description,
        bigBang.statusLabel,
        bigBang.tickDuration,
        bigBang.modelProvider,
        bigBang.modelName,
        bigBang.tags.join(" ")
      ].join(" ").toLowerCase().includes(query);
    }).sort(sorter);
  }

  function filterScenarios(scenarios, query) {
    const normalized = (query || "").trim().toLowerCase();
    if (!normalized) return scenarios;

    return scenarios.filter(function (scenario) {
      return [
        scenario.title,
        scenario.description,
        scenario.category,
        scenario.durationHint,
        scenario.tags.join(" ")
      ].join(" ").toLowerCase().includes(normalized);
    });
  }

  function collectRefs(root) {
    return {
      filters: root.querySelector("[data-bigbang-filters]"),
      summary: root.querySelector("[data-bigbang-summary]"),
      bigBangs: root.querySelector("[data-bigbang-list]"),
      scenarios: root.querySelector("[data-scenario-bank]")
    };
  }

  function resolveRoot(root) {
    if (!root) return document.querySelector("[data-bigbang-slice]");
    if (typeof root === "string") return document.querySelector(root);
    return root;
  }

  function element(tagName, props, children) {
    const node = document.createElement(tagName);
    props = props || {};

    Object.keys(props).forEach(function (key) {
      const value = props[key];
      if (value === null || value === undefined) return;

      if (key === "className") {
        node.className = value;
      } else if (key === "text") {
        node.textContent = value;
      } else if (key === "dataset") {
        Object.keys(value).forEach(function (dataKey) {
          node.dataset[dataKey] = value[dataKey];
        });
      } else if (key.slice(0, 2) === "on" && typeof value === "function") {
        node.addEventListener(key.slice(2), value);
      } else if (key in node) {
        node[key] = value;
      } else {
        node.setAttribute(key, value);
      }
    });

    (children || []).forEach(function (child) {
      if (child) node.appendChild(child);
    });

    return node;
  }

  function rootEvent(name, detail) {
    window.dispatchEvent(new CustomEvent(name, { detail: detail }));
  }

  function getAvailableStatuses(bigBangs) {
    return Array.from(new Set(bigBangs.map(function (bigBang) {
      return bigBang.status;
    }))).sort();
  }

  function normalizeStatus(status) {
    return String(status || "draft").trim().toLowerCase().replace(/\s+/g, "_");
  }

  function normalizeTags(tags) {
    if (!tags) return [];
    if (Array.isArray(tags)) return tags.map(String).filter(Boolean);
    if (typeof tags === "string") {
      return tags.split(",").map(function (tag) {
        return tag.trim();
      }).filter(Boolean);
    }
    return [];
  }

  function numberFrom(value) {
    if (value === null || value === undefined || value === "") return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  }

  function dateValue(value) {
    if (!value) return 0;
    const time = new Date(value).getTime();
    return Number.isFinite(time) ? time : 0;
  }

  function relativeOrDate(value) {
    if (!value) return "Not updated";
    const date = new Date(value);
    if (!Number.isFinite(date.getTime())) return String(value);
    return date.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric"
    });
  }

  function formatNumber(value) {
    return Number(value || 0).toLocaleString();
  }

  function titleCase(value) {
    return String(value || "").replace(/_/g, " ").replace(/\b\w/g, function (match) {
      return match.toUpperCase();
    });
  }

  window.WorldForkBigBangs = {
    createBigBangSlice,
    normalizeBigBang,
    normalizeScenario,
    deriveStatusSummary,
    renderSearchFilterUI,
    renderStatusSummaryCards,
    renderBigBangCards,
    renderScenarioBankCards,
    filterBigBangs,
    filterScenarios
  };

  document.addEventListener("DOMContentLoaded", function () {
    const root = document.querySelector("[data-bigbang-slice][data-autoload]");
    if (!root) return;

    createBigBangSlice({ root: root }).load();
  });
}());
