// Player search: finds a Player by Display Name or Melee username and links each one found to `href(player)`.
const playersReady = fetch("data/players.json").then((response) => response.json());

function playerSearch(input, results, href) {
  playersReady.then((players) => {
    input.addEventListener("input", () => {
      const query = input.value.trim().toLowerCase();
      results.replaceChildren();
      if (!query) return;
      const found = players
        .filter((player) => [player.name, ...player.usernames].some((name) => name.toLowerCase().includes(query)))
        .sort((a, b) => a.name.localeCompare(b.name))
        .slice(0, 20);
      for (const player of found) {
        const item = document.createElement("li");
        const link = document.createElement("a");
        link.href = href(player);
        link.textContent = player.name;
        item.append(link);
        if (player.usernames.some((username) => username !== player.name)) {
          item.append(` (${player.usernames.join(", ")})`);
        }
        results.append(item);
      }
    });
  });
}

// The site search, on every page that has one, opens the Player's card.
const searchInput = document.getElementById("search");
if (searchInput) playerSearch(searchInput, document.getElementById("search-results"), (player) => `player.html#${player.slug}`);
