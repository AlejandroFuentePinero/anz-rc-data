// PROTOTYPE (#11), throwaway: where Compare Players sits on the Player card.
// "tab": the card and the comparison are two tabs; the card's plot, with every compared Player's line, goes with the
// tab that is open, so the comparison is whole in its own space. "beside": the comparison opens in a column beside
// the card where the width allows, and below it on a narrow screen.
(() => {
  const layout = document.querySelector(".card-layout");
  const tabs = document.querySelector(".card-tabs");
  const plot = document.getElementById("against-field");
  const slots = { card: document.getElementById("plot-slot-card"), compare: document.getElementById("plot-slot-compare") };
  const tabbed = document.documentElement.dataset.place === "tab";
  tabs.hidden = !tabbed;

  const parse = () => decodeURIComponent(location.hash.slice(1)).split("/").filter(Boolean);
  let [slug, ...others] = parse();

  function setTab(tab) {
    layout.dataset.tab = tab;
    for (const button of tabs.querySelectorAll("button")) button.setAttribute("aria-selected", button.dataset.tab === tab);
    const slot = tabbed ? slots[tab] : slots.card;
    if (plot.parentElement !== slot) {
      slot.append(plot);
      if (plot.data) requestAnimationFrame(() => Plotly.Plots.resize(plot));
    }
  }

  function count() {
    tabs.querySelector(".tab-count").textContent = others.length ? ` · ${others.length}` : "";
  }

  for (const button of tabs.querySelectorAll("button")) button.addEventListener("click", () => setTab(button.dataset.tab));

  // A link that arrives with Players compared opens on the comparison; a new card opens on the card.
  setTab(tabbed && others.length ? "compare" : "card");
  count();
  window.addEventListener("hashchange", () => {
    const [nextSlug, ...nextOthers] = parse();
    const newCard = nextSlug !== slug;
    [slug, others] = [nextSlug, nextOthers];
    count();
    if (tabbed && newCard) setTab("card");
  });
})();
