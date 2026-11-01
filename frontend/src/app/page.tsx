"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Navbar, TabType } from "../components/Navbar";
import { DashboardOverview } from "../components/DashboardOverview";
import { IngestionTab } from "../components/IngestionTab";
import { ExtractionTab } from "../components/ExtractionTab";
import { SearchAndChatTab } from "../components/SearchAndChatTab";
import { CommitmentTrackerTab } from "../components/CommitmentTrackerTab";
import { api, Memory, CommitmentItem, Company } from "../lib/api";
import { Brain } from "lucide-react";

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabType>("overview");
  const [selectedCompany, setSelectedCompany] = useState<string>("default-org");
  const [companies, setCompanies] = useState<Company[]>([]);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [commitments, setCommitments] = useState<CommitmentItem[]>([]);
  const [analytics, setAnalytics] = useState<any>({});
  const [backendOnline, setBackendOnline] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  // Cross-module pipeline data passing
  const [draftText, setDraftText] = useState<string>("");
  const [draftTitle, setDraftTitle] = useState<string>("");

  // Load backend data
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const health = await api.checkHealth();
      setBackendOnline(health.online);

      if (health.online) {
        const [comps, mems, comms, stats] = await Promise.allSettled([
          api.getCompanies(),
          api.getMemories(selectedCompany),
          api.getCommitments(selectedCompany),
          api.getTrackerAnalytics(selectedCompany),
        ]);

        if (comps.status === "fulfilled" && Array.isArray(comps.value)) {
          setCompanies(comps.value);
        }
        if (mems.status === "fulfilled" && Array.isArray(mems.value)) {
          setMemories(mems.value);
        }
        if (comms.status === "fulfilled" && Array.isArray(comms.value)) {
          setCommitments(comms.value);
        }
        if (stats.status === "fulfilled") {
          setAnalytics(stats.value);
        }
      }
    } catch {
      setBackendOnline(false);
    } finally {
      setLoading(false);
    }
  }, [selectedCompany]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handler for sending text from Ingestion (Mod 1) to Extraction (Mod 2)
  const handleSendToExtraction = (text: string, title: string) => {
    setDraftText(text);
    setDraftTitle(title);
    setActiveTab("extraction");
  };

  const handleBackToDashboard = () => {
    setActiveTab("overview");
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#0b0f19] text-slate-100 selection:bg-blue-600/40">
      {/* Navbar with Module Switcher & Tenant Selector */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        selectedCompany={selectedCompany}
        setSelectedCompany={setSelectedCompany}
        companies={companies}
        backendOnline={backendOnline}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {activeTab === "overview" && (
          <DashboardOverview
            setActiveTab={setActiveTab}
            memories={memories}
            commitments={commitments}
            analytics={analytics}
            loading={loading}
            onRefresh={fetchData}
          />
        )}

        {activeTab === "ingestion" && (
          <IngestionTab
            companyId={selectedCompany}
            onSendToExtraction={handleSendToExtraction}
            onBack={handleBackToDashboard}
          />
        )}

        {activeTab === "extraction" && (
          <ExtractionTab
            companyId={selectedCompany}
            initialText={draftText}
            initialTitle={draftTitle}
            onRefreshMemories={fetchData}
            onBack={handleBackToDashboard}
          />
        )}

        {activeTab === "search-chat" && (
          <SearchAndChatTab
            companyId={selectedCompany}
            onBack={handleBackToDashboard}
          />
        )}

        {activeTab === "tracker" && (
          <CommitmentTrackerTab
            companyId={selectedCompany}
            commitments={commitments}
            analytics={analytics}
            loading={loading}
            onRefresh={fetchData}
            onBack={handleBackToDashboard}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-[#0d131f] py-6 text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-blue-400" />
            <span className="font-bold text-white">AFTERMIND</span>
            <span>— AI-Powered Corporate Memory & Decision Intelligence</span>
          </div>
          <div className="flex items-center gap-4 text-xs font-medium text-slate-400">
            <span>Module 1: Ingestion</span>
            <span>•</span>
            <span>Module 2: Extraction</span>
            <span>•</span>
            <span>Module 3: Memory & RAG</span>
            <span>•</span>
            <span>Module 4: Tracker</span>
            <span>•</span>
            <span className="text-blue-400 font-bold">Module 5: Dashboard</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
