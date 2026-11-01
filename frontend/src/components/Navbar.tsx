"use client";

import React from "react";
import { Brain, Layers, UploadCloud, Cpu, Search, CheckSquare, Building2 } from "lucide-react";

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
    { id: "overview" as TabType, label: "Dashboard", icon: Layers, badge: "Overview" },
    { id: "ingestion" as TabType, label: "Data Ingestion", icon: UploadCloud, badge: "Mod 1" },
    { id: "extraction" as TabType, label: "Memory Extraction", icon: Cpu, badge: "Mod 2" },
    { id: "search-chat" as TabType, label: "AI Search & Assistant", icon: Search, badge: "Mod 3" },
    { id: "tracker" as TabType, label: "Commitment Tracker", icon: CheckSquare, badge: "Mod 4" },
  ];

  return (
    <header className="sticky top-0 z-50 bg-[#0d131f] border-b border-slate-800 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div
            onClick={() => setActiveTab("overview")}
            className="flex items-center gap-3 cursor-pointer group"
          >
            <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center shadow-md shadow-blue-600/30 ring-1 ring-blue-400/40">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <span className="font-bold text-xl tracking-tight text-white group-hover:text-blue-300 transition-colors">
                  AFTERMIND
                </span>
                <span className="text-[11px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded bg-blue-900/60 text-blue-200 border border-blue-700/60">
                  Decision Intelligence
                </span>
              </div>
              <p className="text-xs text-slate-300 font-normal hidden sm:block">
                AI-Powered Organizational Memory & Commitment Tracker
              </p>
            </div>
          </div>

          {/* Controls: Company Context & System Status */}
          <div className="flex items-center gap-3">
            {/* Organization Selector */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs sm:text-sm">
              <Building2 className="w-4 h-4 text-blue-400" />
              <span className="text-slate-300 font-medium">Org:</span>
              <select
                value={selectedCompany}
                onChange={(e) => setSelectedCompany(e.target.value)}
                className="bg-transparent text-white font-semibold focus:outline-none cursor-pointer"
              >
                <option value="default-org" className="bg-slate-900 text-white">
                  default-org
                </option>
                {companies
                  .filter((c) => c.name !== "default-org")
                  .map((c) => (
                    <option key={c.id} value={c.name} className="bg-slate-900 text-white">
                      {c.name}
                    </option>
                  ))}
              </select>
            </div>

            {/* Backend Connection Badge */}
            <div
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs sm:text-sm font-semibold transition-colors ${
                backendOnline
                  ? "bg-emerald-950/60 text-emerald-300 border-emerald-600/50"
                  : "bg-amber-950/60 text-amber-300 border-amber-600/50"
              }`}
            >
              <div
                className={`w-2.5 h-2.5 rounded-full ${
                  backendOnline ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
                }`}
              />
              <span className="hidden sm:inline">
                {backendOnline ? "Backend Connected (4 Modules)" : "Connecting to API..."}
              </span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex space-x-1 sm:space-x-2 border-t border-slate-800/80 overflow-x-auto py-1.5 scrollbar-none">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-2 text-xs sm:text-sm font-semibold rounded-lg transition-all whitespace-nowrap ${
                  isActive
                    ? "bg-blue-600 text-white shadow-sm shadow-blue-600/30"
                    : "text-slate-300 hover:text-white hover:bg-slate-800/70"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-slate-400"}`} />
                <span>{tab.label}</span>
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${
                    isActive
                      ? "bg-blue-800/70 text-blue-100"
                      : "bg-slate-800 text-slate-300 border border-slate-700"
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
