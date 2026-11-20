// Player search: finds a Player by Display Name or Melee username and links to their card.
const searchInput = document.getElementById("search");
const searchResults = document.getElementById("search-results");

fetch("data/players.json")
  .then((response) => response.json())
  .then((players) => {
    searchInput.addEventListener("input", () => {
      const query = searchInput.value.trim().toLowerCase();
      searchResults.replaceChildren();
      if (!query) return;
      const found = players
        .filter((player) => [player.name, ...player.usernames].some((name) => name.toLowerCase().includes(query)))
        .sort((a, b) => a.name.localeCompare(b.name))
        .slice(0, 20);
      for (const player of found) {
        const item = document.createElement("li");
        const link = document.createElement("a");
        link.href = `player.html#${player.slug}`;
        link.textContent = player.name;
        item.append(link);
        if (player.usernames.some((username) => username !== player.name)) {
          item.append(` (${player.usernames.join(", ")})`);
        }
        searchResults.append(item);
      }
    });
  });
