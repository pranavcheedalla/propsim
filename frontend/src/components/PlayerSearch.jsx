import { useEffect, useMemo, useRef, useState } from "react";
import TeamLogo from "./TeamLogo";

// So searching "Jokic" finds "Nikola Jokić" - real player names carry
// diacritics (Jokić, Dončić, Šarić...) that most people won't type.
function normalize(text) {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

export default function PlayerSearch({ players, favorites, selectedPlayer, onSelect, onToggleFavorite }) {
  const [query, setQuery] = useState(selectedPlayer || "");
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const containerRef = useRef(null);
  const listRef = useRef(null);

  useEffect(() => {
    setQuery(selectedPlayer || "");
  }, [selectedPlayer]);

  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
        setQuery(selectedPlayer || "");
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [selectedPlayer]);

  const favoriteSet = useMemo(() => new Set(favorites), [favorites]);

  const results = useMemo(() => {
    const trimmed = normalize(query.trim());
    if (!trimmed || trimmed === normalize(selectedPlayer || "")) {
      const favoritePlayers = players.filter((player) => favoriteSet.has(player.player_name));
      const rest = players.filter((player) => !favoriteSet.has(player.player_name)).slice(0, 40);
      return { favoritePlayers, rest };
    }
    const matches = players
      .filter(
        (player) => normalize(player.player_name).includes(trimmed) || normalize(player.team).includes(trimmed)
      )
      .slice(0, 40);
    return { favoritePlayers: [], rest: matches };
  }, [query, players, favoriteSet, selectedPlayer]);

  const flatResults = useMemo(
    () => [...results.favoritePlayers, ...results.rest],
    [results]
  );

  useEffect(() => {
    setHighlightedIndex(0);
  }, [flatResults.length, isOpen]);

  useEffect(() => {
    if (!isOpen || !listRef.current) return;
    const activeEl = listRef.current.querySelector('[data-active="true"]');
    activeEl?.scrollIntoView({ block: "nearest" });
  }, [highlightedIndex, isOpen]);

  function handleSelect(player) {
    onSelect(player.player_name);
    setQuery(player.player_name);
    setIsOpen(false);
  }

  function handleKeyDown(event) {
    if (!isOpen && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
      setIsOpen(true);
      return;
    }
    if (!isOpen) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlightedIndex((current) => Math.min(current + 1, flatResults.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlightedIndex((current) => Math.max(current - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      const player = flatResults[highlightedIndex];
      if (player) handleSelect(player);
    } else if (event.key === "Escape") {
      setIsOpen(false);
      setQuery(selectedPlayer || "");
    }
  }

  function renderRow(player, flatIndex) {
    const isActive = flatIndex === highlightedIndex;
    return (
      <li
        key={player.player_name}
        id={`player-option-${flatIndex}`}
        role="option"
        aria-selected={isActive}
        data-active={isActive}
        className={`player-search-row${isActive ? " player-search-row--active" : ""}`}
        onMouseEnter={() => setHighlightedIndex(flatIndex)}
        onMouseDown={() => handleSelect(player)}
      >
        <TeamLogo team={player.team} size={22} />
        <span className="player-search-name">{player.player_name}</span>
        <span className="player-search-team muted">{player.team}</span>
        <button
          type="button"
          className={`favorite-star${favoriteSet.has(player.player_name) ? " favorite-star--active" : ""}`}
          aria-label={favoriteSet.has(player.player_name) ? `Remove ${player.player_name} from favorites` : `Add ${player.player_name} to favorites`}
          onMouseDown={(event) => {
            event.stopPropagation();
            event.preventDefault();
            onToggleFavorite(player.player_name);
          }}
        >
          ★
        </button>
      </li>
    );
  }

  let cursor = 0;

  return (
    <div className="player-search" ref={containerRef}>
      <input
        type="text"
        value={query}
        placeholder="Search players..."
        role="combobox"
        aria-expanded={isOpen}
        aria-controls="player-search-listbox"
        aria-autocomplete="list"
        aria-activedescendant={isOpen && flatResults.length > 0 ? `player-option-${highlightedIndex}` : undefined}
        onFocus={() => setIsOpen(true)}
        onClick={() => setIsOpen(true)}
        onKeyDown={handleKeyDown}
        onChange={(event) => {
          setQuery(event.target.value);
          setIsOpen(true);
        }}
      />
      {isOpen && (
        <ul className="player-search-dropdown" id="player-search-listbox" role="listbox" ref={listRef}>
          {results.favoritePlayers.length > 0 && (
            <>
              <li className="player-search-section" role="presentation">
                Favorites
              </li>
              {results.favoritePlayers.map((player) => renderRow(player, cursor++))}
              <li className="player-search-section" role="presentation">
                All players
              </li>
            </>
          )}
          {results.rest.length === 0 ? (
            <li className="player-search-empty muted" role="presentation">
              No players match "{query}"
            </li>
          ) : (
            results.rest.map((player) => renderRow(player, cursor++))
          )}
        </ul>
      )}
    </div>
  );
}
