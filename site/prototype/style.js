// PROTOTYPE (#11), throwaway: the chosen style (B, control-room) with Compare Players beside the card.
// Loads the face and the sheets, themes every Plotly figure, and closes the floating search results once used.
(() => {
  document.write(`<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400..700&display=swap">
<link rel="stylesheet" href="prototype/style.css">`);

  // The page's colours are swapped by value, per page, so the plotting code in the pages stays as signed off.
  const FONT = "Inter, system-ui, sans-serif";
  const COLOURS = {
    community: { "#4a4a4a": "#C9C7BE", "#86b6ef": "#D5DCC9", "#3987e5": "#A8B591", "#1c5cab": "#788C5D", "#0d366b": "#4A5838" },
    player: { "#1c5cab": "#141413", "#c2571a": "#C6613F", "#2a8f7b": "#788C5D", "#7b4fa8": "#6A7FA8", "#c23b6e": "#A68228",
      "#d9a520": "#D4A72C", "#ccc": "#DDDCD6", "#999": "#9C9A92", "#bbb": "#BDBCB6", "#aaa": "#87867F", "#777": "#5E5D59", "#555": "#3D3D3A" },
  };

  const merge = (base, extra) => {
    const out = { ...base };
    for (const [key, value] of Object.entries(extra ?? {})) {
      out[key] = value && typeof value === "object" && !Array.isArray(value) && typeof out[key] === "object" ? merge(out[key], value) : value;
    }
    return out;
  };

  function themed(data, layout) {
    const community = document.querySelector("main")?.classList.contains("community");
    const page = community ? COLOURS.community : COLOURS.player;
    const swap = (value) => (typeof value === "string" && page[value.toLowerCase()]) || value;
    const walk = (value) => (Array.isArray(value) ? value.map(walk)
      : value && typeof value === "object" ? Object.fromEntries(Object.entries(value).map(([key, inner]) => [key, walk(inner)])) : swap(value));
    // The card's plot is read point by point, so its type is a step larger.
    const size = community ? 14 : 15;
    const traces = walk(data);
    for (const trace of traces) {
      // RC size: every bar outlined in ink. The Experience bars keep their white seams.
      if (trace.type === "bar" && community && !trace.name) trace.marker.line = { color: "#141413", width: 1 };
      if (trace.mode?.includes("lines") && trace.marker) {
        trace.line.width = 2;
        trace.textfont = { ...trace.textfont, size: 13, color: "#3D3D3A" };
      }
    }
    const axis = {
      gridcolor: "#EFEEE9", linecolor: "#BDBCB6", zeroline: false, showline: true, ticks: "outside", ticklen: 4, tickcolor: "#BDBCB6",
      tickfont: { size, color: "#3D3D3A" }, title: { font: { size, color: "#141413" } },
    };
    let out = merge(walk(layout), {
      font: { family: FONT, size, color: "#3D3D3A" },
      legend: { font: { size } },
      hoverlabel: { bgcolor: "#FFFFFF", bordercolor: "#BDBCB6", font: { family: FONT, color: "#141413", size: 14 } },
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    });
    out.xaxis = merge(merge(axis, { showgrid: false }), out.xaxis);
    out.yaxis = merge(axis, out.yaxis);
    if (out.annotations) out.annotations = out.annotations.map((note) => merge(note, { font: { size: 13 } }));
    return [traces, out];
  }

  // A plot is drawn at its box's width and redrawn whenever that box changes width, not only when the window does:
  // opening the comparison narrows the card's column without any window resize. Plotly's own resize is not used,
  // since it collapses a plot whose height the page sets.
  const fitted = new WeakSet();
  function fitToColumn(element) {
    if (fitted.has(element)) return;
    fitted.add(element);
    let width = element.clientWidth;
    new ResizeObserver(() => {
      if (!element.clientWidth || element.clientWidth === width) return;
      width = element.clientWidth;
      Plotly.relayout(element, { width });
    }).observe(element);
  }

  if (window.Plotly) {
    for (const name of ["newPlot", "react"]) {
      const original = Plotly[name];
      Plotly[name] = (element, data, layout, config) => {
        const box = typeof element === "string" ? document.getElementById(element) : element;
        const [traces, themedLayout] = themed(data, layout);
        if (box.clientWidth) themedLayout.width = box.clientWidth;
        const drawn = original(box, traces, themedLayout, { ...config, responsive: false });
        fitToColumn(box);
        return drawn;
      };
    }
  }

  // A table cell wraps at its spaces when its column is squeezed, never inside a hyphenated value (29-14-3, Mono-Green).
  function keepWhole(cell) {
    const walker = document.createTreeWalker(cell, NodeFilter.SHOW_TEXT);
    const texts = [];
    while (walker.nextNode()) texts.push(walker.currentNode);
    for (const text of texts) {
      const parts = text.textContent.split(/(\S*-\S*)/);
      if (parts.length === 1) continue;
      text.replaceWith(...parts.map((part, i) => (i % 2 ? Object.assign(document.createElement("span"), { className: "whole", textContent: part }) : part)));
    }
  }

  // The site search's results open over the page, so they close once used or left.
  document.addEventListener("DOMContentLoaded", () => {
    new MutationObserver((changes) => {
      for (const change of changes) for (const node of change.addedNodes) {
        if (node.nodeType !== Node.ELEMENT_NODE) continue;
        (node.matches("td") ? [node] : node.querySelectorAll("td")).forEach(keepWhole);
      }
    }).observe(document.body, { childList: true, subtree: true });
    const box = document.getElementById("search");
    const results = document.getElementById("search-results");
    const close = () => results.replaceChildren();
    window.addEventListener("hashchange", () => { close(); box.value = ""; });
    document.addEventListener("click", (event) => { if (!event.target.closest("header .search")) close(); });
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") close(); });
  });
})();
