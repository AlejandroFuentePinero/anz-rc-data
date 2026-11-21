// PROTOTYPE (#11), throwaway: three styles of the same three pages, switchable from a floating bar.
// ?style=7ph|cr|open picks the look; ?place=tab|beside picks where Compare Players sits on the card.
// Both are remembered across pages, so a link inside the site keeps the style being judged.
(() => {
  const STYLES = [
    { key: "7ph", label: "A · 7ph light",
      fonts: "family=Fraunces:opsz,wght@9..144,600&family=Hanken+Grotesk:wght@400..700" },
    { key: "cr", label: "B · control-room",
      fonts: "family=Inter:wght@400..700&family=Newsreader:opsz,wght@6..72,400..500" },
    { key: "open", label: "C · Unconstrained",
      fonts: "family=Archivo:wdth,wght@62..125,400..800" },
  ];
  const PLACES = [{ key: "tab", label: "Tab" }, { key: "beside", label: "Beside" }];

  const params = new URLSearchParams(location.search);
  const stored = (name) => { try { return localStorage.getItem(`proto-${name}`); } catch { return null; } };
  const pick = (name, list) => [params.get(name), stored(name)].find((key) => list.some((item) => item.key === key)) ?? list[0].key;
  const style = pick("style", STYLES);
  const place = pick("place", PLACES);
  try { localStorage.setItem("proto-style", style); localStorage.setItem("proto-place", place); } catch {}
  params.set("style", style);
  params.set("place", place);
  history.replaceState(null, "", `${location.pathname}?${params}${location.hash}`);

  const root = document.documentElement;
  root.dataset.style = style;
  root.dataset.place = place;
  const { fonts } = STYLES.find((item) => item.key === style);
  document.write(`<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?${fonts}&display=swap">
<link rel="stylesheet" href="prototype/base.css"><link rel="stylesheet" href="prototype/${style}.css">`);

  // ---- Plot themes: each style's chrome and colours, applied over the page's own figure. ----
  // The page's colours are swapped by value, per page, so the plotting code in the pages stays as signed off.
  const THEMES = {
    "7ph": {
      font: { family: "'Hanken Grotesk', system-ui, sans-serif", size: 12, color: "#7d746b" },
      axis: { gridcolor: "#ece6dd", linecolor: "#d9d1c6", zeroline: false, showline: true, title: { font: { size: 12, color: "#7d746b" } } },
      hoverlabel: { bgcolor: "#ffffff", bordercolor: "#e3dcd2", font: { family: "'Hanken Grotesk', sans-serif", color: "#1f1b17", size: 13 } },
      layout: { barcornerradius: 3 },
      community: { "#4a4a4a": "#8a8178", "#86b6ef": "#f6c3a3", "#3987e5": "#ee8f5f", "#1c5cab": "#d95926", "#0d366b": "#9c3a12" },
      player: { "#1c5cab": "#3987e5", "#c2571a": "#d95926", "#2a8f7b": "#199e70", "#7b4fa8": "#9085e9", "#c23b6e": "#d55181",
        "#d9a520": "#c98500", "#ccc": "#ddd5cb", "#999": "#a39a90", "#bbb": "#c9c0b6", "#aaa": "#a39a90", "#777": "#7d746b", "#555": "#7d746b" },
      trace: (trace) => { if (trace.line && trace.mode?.includes("lines") && trace.marker) { trace.line.width = 2; trace.marker.size = 9; } },
    },
    cr: {
      font: { family: "Inter, system-ui, sans-serif", size: 12, color: "#5E5D59" },
      axis: { gridcolor: "#EFEEE9", linecolor: "#BDBCB6", zeroline: false, showline: true, ticks: "outside", ticklen: 4, tickcolor: "#BDBCB6",
        title: { font: { size: 12, color: "#5E5D59" } } },
      xaxis: { showgrid: false },
      hoverlabel: { bgcolor: "#FFFFFF", bordercolor: "#BDBCB6", font: { family: "Inter, sans-serif", color: "#141413", size: 13 } },
      layout: {},
      community: { "#4a4a4a": "#87867F", "#86b6ef": "#D5DCC9", "#3987e5": "#A8B591", "#1c5cab": "#788C5D", "#0d366b": "#4A5838" },
      player: { "#1c5cab": "#141413", "#c2571a": "#C6613F", "#2a8f7b": "#788C5D", "#7b4fa8": "#6A7FA8", "#c23b6e": "#A68228",
        "#d9a520": "#D4A72C", "#ccc": "#DDDCD6", "#999": "#9C9A92", "#bbb": "#BDBCB6", "#aaa": "#9C9A92", "#777": "#5E5D59", "#555": "#5E5D59" },
      trace: (trace) => {
        if (trace.type === "bar" && trace.marker) trace.marker.line = { width: 0 };
        if (trace.line && trace.mode?.includes("lines") && trace.marker) { trace.line.width = 1.5; trace.marker.size = 7; trace.textfont = { ...trace.textfont, size: 10 }; }
      },
    },
    open: {
      font: { family: "Archivo, system-ui, sans-serif", size: 12, color: "#5b6475" },
      axis: { gridcolor: "#e3e6ec", griddash: "dot", linecolor: "#1b2333", zeroline: false, showline: false, tickfont: { size: 12, color: "#1b2333" },
        title: { font: { size: 11, color: "#5b6475" } } },
      xaxis: { showgrid: false, showline: true, linewidth: 2 },
      hoverlabel: { bgcolor: "#10151f", bordercolor: "#10151f", font: { family: "Archivo, sans-serif", color: "#ffffff", size: 13 } },
      layout: { bargap: 0.12 },
      community: { "#4a4a4a": "#1b2333", "#86b6ef": "#c9d6ff", "#3987e5": "#7e9bff", "#1c5cab": "#2f5bff", "#0d366b": "#10226e" },
      player: { "#1c5cab": "#2f5bff", "#c2571a": "#ff5a1f", "#2a8f7b": "#00a37a", "#7b4fa8": "#a23ad1", "#c23b6e": "#d6336c",
        "#d9a520": "#f5b700", "#ccc": "#e3e6ec", "#999": "#8b93a3", "#bbb": "#c4c9d3", "#aaa": "#8b93a3", "#777": "#5b6475", "#555": "#5b6475" },
      trace: (trace) => {
        if (trace.type === "bar" && trace.marker) trace.marker.line = { width: 0 };
        if (trace.line && trace.mode?.includes("lines") && trace.marker) {
          trace.line.width = 3;
          trace.marker.size = 11;
          trace.marker.symbol = "square";
          trace.textfont = { ...trace.textfont, size: 11, color: "#1b2333" };
        }
      },
    },
  };

  const merge = (base, extra) => {
    const out = { ...base };
    for (const [key, value] of Object.entries(extra ?? {})) {
      out[key] = value && typeof value === "object" && !Array.isArray(value) && typeof out[key] === "object" ? merge(out[key], value) : value;
    }
    return out;
  };

  function themed(data, layout) {
    const theme = THEMES[style];
    const page = document.querySelector("main")?.classList.contains("community") ? theme.community : theme.player;
    const swap = (value) => (typeof value === "string" && page[value.toLowerCase()]) || value;
    const walk = (value) => (Array.isArray(value) ? value.map(walk)
      : value && typeof value === "object" ? Object.fromEntries(Object.entries(value).map(([key, inner]) => [key, walk(inner)])) : swap(value));
    const traces = walk(data);
    traces.forEach(theme.trace);
    let out = walk(layout);
    out = merge(out, { font: theme.font, hoverlabel: theme.hoverlabel, paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", ...theme.layout });
    for (const axis of ["xaxis", "yaxis"]) out[axis] = merge(merge(theme.axis, theme[axis]), out[axis]);
    return [traces, out];
  }

  if (window.Plotly) {
    for (const name of ["newPlot", "react"]) {
      const original = Plotly[name];
      Plotly[name] = (element, data, layout, config) => original(element, ...themed(data, layout), config);
    }
  }

  // ---- The floating bar: not part of any design being judged. ----
  const go = (name, key) => {
    const next = new URLSearchParams(location.search);
    next.set(name, key);
    try { localStorage.setItem(`proto-${name}`, key); } catch {}
    location.search = next.toString();
  };
  const step = (by) => {
    const at = STYLES.findIndex((item) => item.key === style);
    go("style", STYLES[(at + by + STYLES.length) % STYLES.length].key);
  };

  document.addEventListener("DOMContentLoaded", () => {
    const bar = document.createElement("div");
    bar.className = "proto-bar";
    const button = (text, title, onClick, pressed) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = text;
      b.title = title;
      if (pressed != null) b.setAttribute("aria-pressed", pressed);
      b.addEventListener("click", onClick);
      return b;
    };
    const label = document.createElement("span");
    label.className = "proto-label";
    label.textContent = STYLES.find((item) => item.key === style).label;
    bar.append(button("‹", "Previous style (←)", () => step(-1)), label, button("›", "Next style (→)", () => step(1)));
    if (document.querySelector("main.player")) {
      const places = document.createElement("span");
      places.className = "proto-places";
      places.append(Object.assign(document.createElement("span"), { textContent: "Compare:" }));
      for (const item of PLACES) places.append(button(item.label, `Where Compare Players sits: ${item.label}`, () => go("place", item.key), item.key === place));
      bar.append(places);
    }
    document.body.append(bar);

    // The search results open over the page, so they close once used or left.
    const lists = ["search-results", "compare-results"].map((id) => document.getElementById(id)).filter(Boolean);
    const close = () => lists.forEach((list) => list.replaceChildren());
    window.addEventListener("hashchange", () => { close(); const box = document.getElementById("search"); if (box) box.value = ""; });
    document.addEventListener("click", (event) => { if (!event.target.closest(".search")) close(); });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") close();
      if (event.target.closest("input, textarea, [contenteditable]")) return;
      if (event.key === "ArrowLeft") step(-1);
      if (event.key === "ArrowRight") step(1);
    });
  });
})();
