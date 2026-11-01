"use client";

import React from "react";
import { Brain, Layers, UploadCloud, Cpu, Search, CheckSquare, Sparkles, Building2 } from "lucide-react";

export type TabType = "overview" | "ingestion" | "extraction" | "search-chat" | "tracker";

interface NavbarProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  selectedCompany: string;
  setSelectedCompany: (company: string) => void;
  companies: Array<{ id: string; name: string }>;
  backendOnline: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  selectedCompany,
  setSelectedCompany,
  companies,
  backendOnline,
}) => {
  const tabs = [
    { id: "overview" as TabType, label: "Overview", icon: Layers, badge: "Dashboard" },
    { id: "ingestion" as TabType, label: "Data Ingestion", icon: UploadCloud, badge: "Mod 1" },
    { id: "extraction" as TabType, label: "Memory Extraction", icon: Cpu, badge: "Mod 2" },
    { id: "search-chat" as TabType, label: "Search & AI Assistant", icon: Search, badge: "Mod 3" },
    { id: "tracker" as TabType, label: "Commitment Tracker", icon: CheckSquare, badge: "Mod 4" },
  ];

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/25 ring-1 ring-white/20">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-white via-slate-100 to-indigo-200 bg-clip-text text-transparent">
                  AFTERMIND
                </span>
                <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  AI Memory Platform
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">
                Remember. Understand. Act on Business Intelligence.
              </p>
            </div>
          </div>

          {/* Company Context & Backend Status */}
          <div className="flex items-center gap-3">
            {/* Workspace / Company selector */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs">
              <Building2 className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-slate-400">Org:</span>
              <select
                value={selectedCompany}
                onChange={(e) => setSelectedCompany(e.target.value)}
                className="bg-transparent text-slate-200 font-medium focus:outline-none cursor-pointer"
              >
                <option value="default-org" className="bg-slate-900 text-slate-200">
                  default-org
                </option>
                {companies
                  .filter((c) => c.name !== "default-org")
                  .map((c) => (
                    <option key={c.id} value={c.name} className="bg-slate-900 text-slate-200">
                      {c.name}
                    </option>
                  ))}
              </select>
            </div>

            {/* Backend Connection Indicator */}
            <div
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
                backendOnline
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                  : "bg-amber-500/10 text-amber-400 border-amber-500/30"
              }`}
            >
              <div
                className={`w-2 h-2 rounded-full ${
                  backendOnline ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
                }`}
              />
              <span className="hidden md:inline">
                {backendOnline ? "API Online (4 Modules)" : "Backend Connecting..."}
              </span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex space-x-1 sm:space-x-2 border-t border-slate-800/60 overflow-x-auto py-1 scrollbar-none">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-2 text-xs sm:text-sm font-medium rounded-lg transition-all whitespace-nowrap ${
                  isActive
                    ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 shadow-sm shadow-indigo-500/10"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-indigo-400" : "text-slate-400"}`} />
                <span>{tab.label}</span>
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded font-semibold ${
                    isActive
                      ? "bg-indigo-500/30 text-indigo-200"
                      : "bg-slate-800 text-slate-400"
                  }`}
                >
                  {tab.badge}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};
