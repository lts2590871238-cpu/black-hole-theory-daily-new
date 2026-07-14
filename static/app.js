"use strict";

const formatLatexCitations = () => {
  const pattern = /\\(?:cite|citep|citet)\*?(?:\[[^\]\n]*\]){0,2}\{([^{}\n]+)\}/g;
  document.querySelectorAll(".mathjax_process").forEach((root) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) {
      if (!walker.currentNode.parentElement?.closest("script, style, code, pre, mjx-container")) {
        nodes.push(walker.currentNode);
      }
    }
    nodes.forEach((node) => {
      const text = node.nodeValue || "";
      pattern.lastIndex = 0;
      if (!pattern.test(text)) return;
      pattern.lastIndex = 0;
      const fragment = document.createDocumentFragment();
      let cursor = 0;
      for (const match of text.matchAll(pattern)) {
        const index = match.index || 0;
        fragment.append(document.createTextNode(text.slice(cursor, index)));
        const keys = match[1].split(",").map((key) => key.trim()).filter(Boolean);
        const citation = document.createElement("span");
        citation.className = "citation-token";
        citation.textContent = `[${keys.join(", ")}]`;
        citation.setAttribute("aria-label", `引用 ${keys.join("、")}`);
        fragment.append(citation);
        cursor = index + match[0].length;
      }
      fragment.append(document.createTextNode(text.slice(cursor)));
      node.replaceWith(fragment);
    });
  });
};

window.addEventListener("load", () => {
  const startup = window.MathJax?.startup?.promise;
  if (startup && typeof startup.then === "function") {
    startup.then(formatLatexCitations).catch(formatLatexCitations);
  } else {
    formatLatexCitations();
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const cards = Array.from(document.querySelectorAll("[data-paper]"));
  const search = document.querySelector("#search");
  const dateScope = document.querySelector("#date-scope");
  const day = document.querySelector("#day-filter");
  const month = document.querySelector("#month-filter");
  const year = document.querySelector("#year-filter");
  const dateFrom = document.querySelector("#date-from");
  const dateTo = document.querySelector("#date-to");
  const dayField = document.querySelector("#day-field");
  const monthField = document.querySelector("#month-field");
  const yearField = document.querySelector("#year-field");
  const rangeFields = document.querySelector("#range-fields");
  const score = document.querySelector("#score-filter");
  const scoreOutput = document.querySelector("#score-output");
  const source = document.querySelector("#source-filter");
  const reset = document.querySelector("#reset-filters");
  const count = document.querySelector("#visible-count");
  const empty = document.querySelector("#no-results");
  const chips = Array.from(document.querySelectorAll("[data-topic]"));
  if (!search || !dateScope || !day || !month || !year || !dateFrom || !dateTo ||
      !dayField || !monthField || !yearField || !rangeFields || !score ||
      !scoreOutput || !source || !reset) return;
  let activeTopic = "";

  const matchesDate = (paperDate) => {
    if (dateScope.value === "day") return !day.value || paperDate === day.value;
    if (dateScope.value === "month") return !month.value || paperDate.startsWith(month.value);
    if (dateScope.value === "year") {
      return !/^\d{4}$/.test(year.value) || paperDate.startsWith(`${year.value}-`);
    }
    if (dateScope.value === "range") {
      return (!dateFrom.value || paperDate >= dateFrom.value) &&
        (!dateTo.value || paperDate <= dateTo.value);
    }
    return true;
  };

  const syncDateControls = () => {
    dayField.hidden = dateScope.value !== "day";
    monthField.hidden = dateScope.value !== "month";
    yearField.hidden = dateScope.value !== "year";
    rangeFields.hidden = dateScope.value !== "range";
  };

  const apply = () => {
    const query = search.value.trim().toLocaleLowerCase();
    const minimum = Number(score.value);
    let visible = 0;
    cards.forEach((card) => {
      const show = (!query || card.dataset.search.includes(query)) &&
        matchesDate(card.dataset.date) &&
        (!source.value || card.dataset.sources.includes(source.value)) &&
        (!activeTopic || card.dataset.topic === activeTopic) &&
        Number(card.dataset.score) >= minimum;
      card.hidden = !show;
      if (show) visible += 1;
    });
    scoreOutput.value = String(minimum);
    if (count) count.textContent = String(visible);
    if (empty) empty.hidden = visible !== 0;
  };

  [search, day, month, year, dateFrom, dateTo, score, source].forEach((control) =>
    control.addEventListener("input", apply));
  dateScope.addEventListener("change", () => { syncDateControls(); apply(); });
  chips.forEach((chip) => chip.addEventListener("click", () => {
    activeTopic = chip.dataset.topic || "";
    chips.forEach((item) => item.classList.toggle("active", item === chip));
    apply();
  }));
  reset.addEventListener("click", () => {
    search.value = ""; dateScope.value = "all"; day.value = ""; month.value = "";
    year.value = ""; dateFrom.value = ""; dateTo.value = ""; score.value = "0";
    source.value = ""; activeTopic = "";
    chips.forEach((item, index) => item.classList.toggle("active", index === 0));
    syncDateControls(); apply();
  });
  syncDateControls();
});
