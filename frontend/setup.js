(function () {
  "use strict";

  var DEFAULT_SIMULATION_CONFIG = {
    tick_duration: "1 day",
    max_ticks: 30,
    initial_root_timelines: 1,
    max_branch_depth: 4,
    max_active_multiverses: 12,
    sociology_preset: "default",
    emotion_observability_enabled: true,
    dependency_graph_enabled: true
  };

  var DEFAULT_BRANCH_POLICY = {
    max_branches_per_tick: 3,
    branch_score_threshold: 0.72,
    allow_recursive_branching: true,
    god_agent_authorization_required: true
  };

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function prettyJson(value) {
    return JSON.stringify(value, null, 2);
  }

  function parseJsonField(form, name, fallback) {
    var field = form.elements[name];
    var raw = field ? field.value.trim() : "";

    if (!raw) {
      return fallback;
    }

    try {
      return JSON.parse(raw);
    } catch (error) {
      markFieldInvalid(field, "Use valid JSON. " + error.message);
      throw error;
    }
  }

  function markFieldInvalid(input, message) {
    if (!input) {
      return;
    }

    var field = input.closest(".wf-setup-field");
    var error = field ? field.querySelector(".wf-setup-error") : null;

    if (field) {
      field.dataset.invalid = "true";
    }

    if (error) {
      error.textContent = message;
    }
  }

  function clearInvalid(form) {
    Array.prototype.forEach.call(form.querySelectorAll("[data-invalid]"), function (field) {
      field.removeAttribute("data-invalid");
    });
  }

  function collectBigBangPayload(form) {
    clearInvalid(form);

    var name = form.elements.name.value.trim();
    var scenarioText = form.elements.scenario_text.value.trim();
    var description = form.elements.description.value.trim();

    if (!name) {
      markFieldInvalid(form.elements.name, "Name is required.");
      throw new Error("Big Bang name is required.");
    }

    if (!scenarioText) {
      markFieldInvalid(form.elements.scenario_text, "Scenario text is required.");
      throw new Error("Scenario text is required.");
    }

    return {
      name: name,
      description: description,
      scenario_text: scenarioText,
      simulation_config: parseJsonField(form, "simulation_config", DEFAULT_SIMULATION_CONFIG),
      branch_policy: parseJsonField(form, "branch_policy", DEFAULT_BRANCH_POLICY),
      use_initializer_agent: Boolean(form.elements.use_initializer_agent.checked),
      initializer_prompt: form.elements.initializer_prompt.value.trim()
    };
  }

  function importPlainTextFile(file, target, statusNode) {
    if (!file || !target) {
      return;
    }

    var reader = new FileReader();

    reader.onload = function () {
      var text = String(reader.result || "");
      target.value = target.value ? target.value + "\n\n" + text : text;
      target.dispatchEvent(new Event("input", { bubbles: true }));

      if (statusNode) {
        statusNode.textContent = "Imported plain text from " + file.name + ".";
      }
    };

    reader.onerror = function () {
      if (statusNode) {
        statusNode.textContent = "Could not import " + file.name + ". Paste the extracted text instead.";
      }
    };

    reader.readAsText(file);
  }

  function renderSetupPage(root, options) {
    var opts = options || {};

    root.innerHTML = [
      '<main class="wf-setup">',
      '  <div class="wf-setup-shell">',
      '    <aside class="wf-setup-hero" aria-label="Big Bang setup overview">',
      '      <p class="wf-setup-kicker">WorldFork setup</p>',
      '      <h1 class="wf-setup-title">Create a Big Bang</h1>',
      '      <p class="wf-setup-copy">Seed one scenario, configure the branching rules, then enter a single research workspace where every timeline, tick, event, and God Agent decision remains inspectable.</p>',
      '      <ul class="wf-setup-rules">',
      '        <li class="wf-setup-rule">PDF material is text-only here: paste extracted text or import a plain-text export.</li>',
      '        <li class="wf-setup-rule">Advanced simulation and branch controls stay visible as JSON snapshots so the API payload remains explicit.</li>',
      '        <li class="wf-setup-rule">Initializer prompts can scaffold actors and cohorts without hiding the root scenario.</li>',
      '      </ul>',
      '    </aside>',
      '    <section class="wf-setup-panel" aria-label="New Big Bang form">',
      '      <form class="wf-setup-form" data-wf-setup-form>',
      '        <div class="wf-setup-section">',
      '          <h2>Root scenario</h2>',
      '          <p>Name the workspace and paste the scenario text that the first multiverse timeline starts from.</p>',
      '          <div class="wf-setup-grid">',
      fieldHtml("name", "Name", "input", "e.g. The Bay Area transit strike", "Human-facing Big Bang title.", true),
      fieldHtml("description", "Description", "textarea", "Optional short research framing.", "Shown in setup summaries and selection lists.", false),
      fieldHtml("scenario_text", "Scenario text", "textarea", "Paste the root scenario, notes, article excerpts, or extracted PDF text.", "Required. This is the source scenario for the Big Bang.", true, "wf-wide"),
      '            <div class="wf-setup-field wf-wide">',
      '              <span class="wf-setup-label">Plain-text import</span>',
      '              <div class="wf-setup-doc-import">',
      '                <input class="wf-setup-file" type="file" data-wf-document-import accept=".txt,.md,.text,.csv,.json,.pdf">',
      '                <button class="wf-setup-button secondary" type="button" data-wf-clear-document>Clear scenario</button>',
      '              </div>',
      '              <span class="wf-setup-hint">No PDF parsing is performed. If you choose a PDF, the browser only reads it as plain text; paste extracted text for reliable input.</span>',
      '            </div>',
      '          </div>',
      '        </div>',
      '        <div class="wf-setup-section">',
      '          <h2>Simulation controls</h2>',
      '          <p>These snapshots line up with the backend BigBangCreate payload and remain editable before submit.</p>',
      '          <div class="wf-setup-grid">',
      fieldHtml("simulation_config", "Simulation config", "textarea", prettyJson(DEFAULT_SIMULATION_CONFIG), "JSON: tick duration, limits, presets, and observability flags.", true, "wf-wide", true),
      fieldHtml("branch_policy", "Branch policy", "textarea", prettyJson(DEFAULT_BRANCH_POLICY), "JSON: branch fanout, score threshold, recursive branching, and God Agent authorization.", true, "wf-wide", true),
      '          </div>',
      '        </div>',
      '        <div class="wf-setup-section">',
      '          <h2>Initializer agent</h2>',
      '          <p>Optionally ask an initializer agent to derive the first actor registry, cohorts, heroes, and channels from the scenario.</p>',
      '          <label class="wf-setup-toggle">',
      '            <input type="checkbox" name="use_initializer_agent" checked>',
      '            <span><strong>Use initializer agent</strong><span class="wf-setup-hint">When disabled, the backend should use deterministic defaults or a later manual setup path.</span></span>',
      '          </label>',
      '          <div class="wf-setup-grid" style="margin-top:16px">',
      fieldHtml("initializer_prompt", "Initializer prompt", "textarea", "Extract initial cohorts, hero actors, public channels, social-media surfaces, and unresolved tensions. Keep emotion observations inspectable but do not feed them forward as hidden steering.", "Sent only when the initializer agent is enabled.", false, "wf-wide"),
      '          </div>',
      '        </div>',
      '        <div class="wf-setup-actions">',
      '          <span class="wf-setup-status" data-wf-setup-status>Ready to create a Big Bang payload.</span>',
      '          <div>',
      '            <button class="wf-setup-button secondary" type="button" data-wf-save-draft>Save draft</button>',
      '            <button class="wf-setup-button" type="submit">Create Big Bang</button>',
      '          </div>',
      '        </div>',
      '      </form>',
      '    </section>',
      '  </div>',
      '</main>'
    ].join("");

    var form = root.querySelector("[data-wf-setup-form]");
    var statusNode = root.querySelector("[data-wf-setup-status]");
    var scenarioInput = form.elements.scenario_text;
    var fileInput = root.querySelector("[data-wf-document-import]");
    var initializerToggle = form.elements.use_initializer_agent;
    var initializerPrompt = form.elements.initializer_prompt;

    restoreDraft(form, opts.storageKey);
    syncInitializerState(initializerToggle, initializerPrompt);

    initializerToggle.addEventListener("change", function () {
      syncInitializerState(initializerToggle, initializerPrompt);
    });

    fileInput.addEventListener("change", function () {
      importPlainTextFile(fileInput.files[0], scenarioInput, statusNode);
      fileInput.value = "";
    });

    root.querySelector("[data-wf-clear-document]").addEventListener("click", function () {
      scenarioInput.value = "";
      statusNode.textContent = "Scenario text cleared.";
    });

    root.querySelector("[data-wf-save-draft]").addEventListener("click", function () {
      saveDraft(form, opts.storageKey);
      statusNode.textContent = "Draft saved in this browser.";
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();

      try {
        var payload = collectBigBangPayload(form);
        statusNode.textContent = "Big Bang payload created.";

        if (typeof opts.onSubmit === "function") {
          opts.onSubmit(payload, form);
        }

        root.dispatchEvent(new CustomEvent("worldfork:bigbang-create", {
          bubbles: true,
          detail: { payload: payload }
        }));
      } catch (error) {
        statusNode.textContent = error.message;
      }
    });

    return form;
  }

  function fieldHtml(name, label, type, placeholder, hint, required, className, jsonField) {
    var tag = type === "textarea" ? "textarea" : "input";
    var attrs = [
      'name="' + escapeHtml(name) + '"',
      'placeholder="' + escapeHtml(placeholder) + '"'
    ];

    if (required) {
      attrs.push("required");
    }

    if (jsonField) {
      attrs.push("data-json-field");
    }

    if (tag === "input") {
      attrs.push('type="text"');
    }

    return [
      '            <label class="wf-setup-field ' + escapeHtml(className || "") + '">',
      '              <span class="wf-setup-label">' + escapeHtml(label) + (required ? "<span>Required</span>" : "") + '</span>',
      tag === "textarea"
        ? '              <textarea ' + attrs.join(" ") + ">" + (jsonField ? escapeHtml(placeholder) : "") + "</textarea>"
        : '              <input ' + attrs.join(" ") + ">",
      '              <span class="wf-setup-hint">' + escapeHtml(hint) + '</span>',
      '              <span class="wf-setup-error"></span>',
      '            </label>'
    ].join("");
  }

  function syncInitializerState(toggle, prompt) {
    prompt.disabled = !toggle.checked;
    prompt.closest(".wf-setup-field").style.opacity = toggle.checked ? "1" : "0.58";
  }

  function saveDraft(form, storageKey) {
    if (!window.localStorage) {
      return;
    }

    var payload = {
      name: form.elements.name.value,
      description: form.elements.description.value,
      scenario_text: form.elements.scenario_text.value,
      simulation_config: form.elements.simulation_config.value,
      branch_policy: form.elements.branch_policy.value,
      use_initializer_agent: form.elements.use_initializer_agent.checked,
      initializer_prompt: form.elements.initializer_prompt.value
    };

    window.localStorage.setItem(storageKey || "worldfork.setupDraft", JSON.stringify(payload));
  }

  function restoreDraft(form, storageKey) {
    if (!window.localStorage) {
      return;
    }

    var raw = window.localStorage.getItem(storageKey || "worldfork.setupDraft");

    if (!raw) {
      return;
    }

    try {
      var payload = JSON.parse(raw);
      Object.keys(payload).forEach(function (name) {
        if (!form.elements[name]) {
          return;
        }

        if (form.elements[name].type === "checkbox") {
          form.elements[name].checked = Boolean(payload[name]);
        } else {
          form.elements[name].value = payload[name];
        }
      });
    } catch (error) {
      window.localStorage.removeItem(storageKey || "worldfork.setupDraft");
    }
  }

  window.WorldForkSetup = {
    DEFAULT_SIMULATION_CONFIG: DEFAULT_SIMULATION_CONFIG,
    DEFAULT_BRANCH_POLICY: DEFAULT_BRANCH_POLICY,
    collectBigBangPayload: collectBigBangPayload,
    importPlainTextFile: importPlainTextFile,
    renderSetupPage: renderSetupPage
  };

  document.addEventListener("DOMContentLoaded", function () {
    var root = document.querySelector("[data-worldfork-setup]");

    if (!root && document.body && document.body.dataset.page === "setup") {
      root = document.querySelector("#app");
    }

    if (root && !root.dataset.wfSetupMounted) {
      root.dataset.wfSetupMounted = "true";
      renderSetupPage(root);
    }
  });
}());
