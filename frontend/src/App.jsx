import { useEffect, useState } from "react";
import PlayerPropTab from "./components/PlayerPropTab";
import GameMoneylineTab from "./components/GameMoneylineTab";
import BacktestTab from "./components/BacktestTab";
import BetTrackerTab from "./components/BetTrackerTab";
import ErrorBoundary from "./components/ErrorBoundary";
import { ToastProvider } from "./components/ToastProvider";
import useLocalStorage from "./hooks/useLocalStorage";
import "./App.css";

const TABS = [
  { id: "prop", label: "Player Props" },
  { id: "game", label: "Game Moneyline" },
  { id: "bets", label: "Bet Tracker" },
  { id: "backtest", label: "Backtest Stats" },
];

function ThemeToggle() {
  const [theme, setTheme] = useLocalStorage("propsim:theme", "dark");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
    >
      {theme === "dark" ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      )}
    </button>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState("prop");

  return (
    <ToastProvider>
      <div className="app">
        <header className="app-header">
          <span className="app-mark">PS</span>
          <div className="app-header-text">
            <h1>PropSim</h1>
            <p className="muted">Monte Carlo player prop &amp; moneyline predictions, backed by a C++ simulation engine</p>
          </div>
          <ThemeToggle />
        </header>

        <nav className="tab-nav">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={activeTab === tab.id ? "tab-button tab-button--active" : "tab-button"}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <main>
          <ErrorBoundary key={activeTab}>
            {activeTab === "prop" && <PlayerPropTab />}
            {activeTab === "game" && <GameMoneylineTab />}
            {activeTab === "bets" && <BetTrackerTab />}
            {activeTab === "backtest" && <BacktestTab />}
          </ErrorBoundary>
        </main>

        <footer className="app-footer">
          <p className="muted">Data pulled from the real NBA (2023-24 through 2025-26) via nba_api, plus live odds/injuries from ESPN.</p>
        </footer>
      </div>
    </ToastProvider>
  );
}
