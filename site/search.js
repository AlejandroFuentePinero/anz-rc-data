// Player search: finds a Player by Display Name or Melee username and links each one found to `href(player)`.
const playersReady = fetch("data/players.json").then((response) => response.json());

function playerSearch(input, results, href) {
  playersReady.then((players) => {
    input.addEventListener("input", () => {
      const query = input.value.trim().toLowerCase();
      results.replaceChildren();
      if (!query) return;
      // An exact name first, then a name that starts with the query, then any that contains it, so a short
      // username like "na" is not crowded out of the 20 by names that only contain it.
      const closeness = (player) =>
        Math.min(...[player.name, ...player.usernames].map((name) => {
          name = name.toLowerCase();
          return name === query ? 0 : name.startsWith(query) ? 1 : name.includes(query) ? 2 : 3;
        }));
      const found = players
        .map((player) => [closeness(player), player])
        .filter(([rank]) => rank < 3)
        .sort(([a, x], [b, y]) => a - b || x.name.localeCompare(y.name))
        .map(([, player]) => player)
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

// The site search opens the Player's card.
playerSearch(document.getElementById("search"), document.getElementById("search-results"), (player) => `player.html#${player.slug}`);
