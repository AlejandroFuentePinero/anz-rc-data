// What the pages share: table text that keeps its hyphenated values whole, plots drawn in the site's type, and the
// pointer label.

// A cell's text with every hyphenated value (29-14-3, Mono-Green, 2-3) in one unbreakable piece, so a squeezed column
// wraps only at spaces.
function whole(value) {
  const parts = String(value).split(/(\S*-\S*)/);
  const fragment = document.createDocumentFragment();
  parts.forEach((part, i) => {
    if (i % 2) fragment.append(Object.assign(document.createElement("span"), { className: "whole", textContent: part }));
    else if (part) fragment.append(part);
  });
  return fragment;
}

// A view's name in the interface: every Format together is Global in the data and the URLs, and reads as All.
const viewName = (view) => (view === "Global" ? "All" : view);

const PLOT_FONT = "Inter, system-ui, sans-serif";

// A plot in Inter at `size` px with light grids and outside ticks, its margins grown to fit its tick labels and axis
// titles. The page sets its own colours.
function drawPlot(id, data, layout, size) {
  const box = document.getElementById(id);
  const axis = {
    gridcolor: "#EFEEE9", linecolor: "#BDBCB6", zeroline: false, showline: true, ticks: "outside", ticklen: 4, tickcolor: "#BDBCB6",
    tickfont: { size, color: "#3D3D3A" }, automargin: true,
  };
  const withAxis = (base, own = {}) => ({ ...base, ...own, title: { font: { size, color: "#141413" }, standoff: 12, ...own.title } });
  Plotly.react(box, data, {
    ...layout,
    width: box.clientWidth || undefined,
    font: { family: PLOT_FONT, size, color: "#3D3D3A" },
    legend: { ...layout.legend, font: { size } },
    hoverlabel: { bgcolor: "#FFFFFF", bordercolor: "#BDBCB6", font: { family: PLOT_FONT, color: "#141413", size: 14 } },
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    xaxis: withAxis({ ...axis, showgrid: false }, layout.xaxis),
    yaxis: withAxis(axis, layout.yaxis),
  }, { displayModeBar: false });
  fitToColumn(box);
}

// A plot is redrawn whenever its box changes width, not only when the window does: opening a comparison narrows the
// card's column with no window resize. Plotly's own resize is not used, since it collapses a plot whose height the
// page sets.
const fitted = new WeakSet();
function fitToColumn(box) {
  if (fitted.has(box)) return;
  fitted.add(box);
  let width = box.clientWidth;
  new ResizeObserver(() => {
    if (!box.clientWidth || box.clientWidth === width) return;
    width = box.clientWidth;
    Plotly.relayout(box, { width });
  }).observe(box);
}

// The pointer label follows the pointer over anything that carries a data-tip, at once where a title would wait.
const tip = Object.assign(document.createElement("div"), { className: "tip", hidden: true });
document.body.append(tip);
document.addEventListener("mousemove", (event) => {
  const said = event.target.closest("[data-tip]")?.dataset.tip;
  tip.hidden = !said;
  if (!said) return;
  tip.textContent = said;
  tip.style.left = `${Math.min(event.clientX + 12, innerWidth - tip.offsetWidth - 8)}px`;
  tip.style.top = `${event.clientY + 16}px`;
});
