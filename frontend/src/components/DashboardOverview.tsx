"use client";

import React from "react";
import {
  Brain,
  UploadCloud,
  Cpu,
  Search,
  CheckSquare,
  AlertTriangle,
  Clock,
  ArrowRight,
  ShieldCheck,
  Sparkles,
  Layers,
  FileText,
  Calendar,
} from "lucide-react";
import { TabType } from "./Navbar";
import { Memory, CommitmentItem } from "../lib/api";

interface DashboardOverviewProps {
  setActiveTab: (tab: TabType) => void;
  memories: Memory[];
  commitments: CommitmentItem[];
  analytics: {
    total?: number;
    active?: number;
    completed?: number;
    overdue?: number;
    completion_rate?: number;
  };
  loading: boolean;
  onRefresh: () => void;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  setActiveTab,
  memories,
  commitments,
  analytics,
  loading,
  onRefresh,
}) => {
  const decisions = memories.filter((m) => m.memory_type === "decision");
  const requirements = memories.filter((m) => m.memory_type === "client_requirement");
  const overdueCount = analytics.overdue ?? commitments.filter((c) => c.status === "OVERDUE").length;
  const activeCount = analytics.active ?? commitments.filter((c) => c.status === "ACTIVE").length;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-950/80 via-slate-900/90 to-purple-950/70 border border-indigo-500/20 p-6 sm:p-8 shadow-2xl">
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-80 h-80 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-semibold mb-4">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI-Powered Business Memory Platform</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight">
            Don't Just Store Information. <br />
            <span className="bg-gradient-to-r from-indigo-400 via-purple-300 to-pink-300 bg-clip-text text-transparent">
              Remember, Understand and Act on It.
            </span>
          </h1>
          <p className="mt-3 text-sm sm:text-base text-slate-300 leading-relaxed">
            AFTERMIND unifies documents, meeting recordings, and conversations into a connected organizational memory. Never lose historical context, track commitments, and query with AI assistance.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              onClick={() => setActiveTab("ingestion")}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs sm:text-sm shadow-lg shadow-indigo-600/30 transition-all hover:scale-[1.02]"
            >
              <UploadCloud className="w-4 h-4" />
              Ingest Document or Audio
            </button>
            <button
              onClick={() => setActiveTab("search-chat")}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-slate-700 font-medium text-xs sm:text-sm transition-all hover:scale-[1.02]"
            >
              <Search className="w-4 h-4 text-indigo-400" />
              Ask AI Assistant
            </button>
            <button
              onClick={() => setActiveTab("tracker")}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-slate-700 font-medium text-xs sm:text-sm transition-all hover:scale-[1.02]"
            >
              <CheckSquare className="w-4 h-4 text-emerald-400" />
              Track Commitments
            </button>
          </div>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Memories */}
        <div className="glass-card p-5 rounded-xl border border-slate-800 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Total Business Memories
            </span>
            <div className="w-9 h-9 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
              <Brain className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">
              {loading ? "..." : memories.length}
            </span>
            <span className="text-xs text-indigo-300 font-medium">Stored Entities</span>
          </div>
          <div className="mt-2 text-xs text-slate-400 flex items-center gap-2">
            <span>{decisions.length} Decisions</span>
            <span>•</span>
            <span>{requirements.length} Requirements</span>
          </div>
        </div>

        {/* Active Commitments */}
        <div className="glass-card p-5 rounded-xl border border-slate-800 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Active Commitments
            </span>
            <div className="w-9 h-9 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-emerald-400">
              {loading ? "..." : activeCount}
            </span>
            <span className="text-xs text-emerald-300/80 font-medium">In Progress</span>
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Completion rate: {analytics.completion_rate ?? 0}%
          </div>
        </div>

        {/* Overdue Alerts */}
        <div className="glass-card p-5 rounded-xl border border-slate-800 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Overdue / Critical
            </span>
            <div
              className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                overdueCount > 0 ? "bg-rose-500/20 text-rose-400" : "bg-slate-800 text-slate-400"
              }`}
            >
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span
              className={`text-3xl font-extrabold ${
                overdueCount > 0 ? "text-rose-400" : "text-slate-300"
              }`}
            >
              {loading ? "..." : overdueCount}
            </span>
            <span className="text-xs text-slate-400 font-medium">Action Items</span>
          </div>
          <div className="mt-2 text-xs text-slate-400">
            {overdueCount > 0 ? "Requires immediate follow-up" : "All deadlines on schedule"}
          </div>
        </div>

        {/* AI Vector Memory Engine */}
        <div className="glass-card p-5 rounded-xl border border-slate-800 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Vector Intelligence
            </span>
            <div className="w-9 h-9 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-purple-300">1536</span>
            <span className="text-xs text-purple-300 font-medium">Dim Vectors</span>
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Multi-LLM & Hybrid RAG Active
          </div>
        </div>
      </div>

      {/* Module Flow Architecture Cards */}
      <div>
        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <Layers className="w-5 h-5 text-indigo-400" />
          End-to-End Intelligence Pipeline
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div
            onClick={() => setActiveTab("ingestion")}
            className="p-4 rounded-xl glass-card border border-slate-800 hover:border-indigo-500/50 cursor-pointer group"
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">
                Module 1
              </span>
              <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 group-hover:translate-x-1 transition-all" />
            </div>
            <h3 className="font-semibold text-slate-200 mt-2">Data Ingestion</h3>
            <p className="text-xs text-slate-400 mt-1">
              Extract raw text from PDF, DOCX, TXT, or transcribe MP3, WAV, M4A audio.
            </p>
          </div>

          <div
            onClick={() => setActiveTab("extraction")}
            className="p-4 rounded-xl glass-card border border-slate-800 hover:border-indigo-500/50 cursor-pointer group"
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-purple-400 uppercase tracking-wider">
                Module 2
              </span>
              <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-purple-400 group-hover:translate-x-1 transition-all" />
            </div>
            <h3 className="font-semibold text-slate-200 mt-2">Memory Extraction</h3>
            <p className="text-xs text-slate-400 mt-1">
              AI parses decisions, commitments, requirements, entities, and confidence scores.
            </p>
          </div>

          <div
            onClick={() => setActiveTab("search-chat")}
            className="p-4 rounded-xl glass-card border border-slate-800 hover:border-indigo-500/50 cursor-pointer group"
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-blue-400 uppercase tracking-wider">
                Module 3
              </span>
              <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-blue-400 group-hover:translate-x-1 transition-all" />
            </div>
            <h3 className="font-semibold text-slate-200 mt-2">Connected Memory & RAG</h3>
            <p className="text-xs text-slate-400 mt-1">
              Persistent vector search and conversational assistant with verifiable citations.
            </p>
          </div>

          <div
            onClick={() => setActiveTab("tracker")}
            className="p-4 rounded-xl glass-card border border-slate-800 hover:border-indigo-500/50 cursor-pointer group"
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">
                Module 4
              </span>
              <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-emerald-400 group-hover:translate-x-1 transition-all" />
            </div>
            <h3 className="font-semibold text-slate-200 mt-2">Commitment Tracker</h3>
            <p className="text-xs text-slate-400 mt-1">
              Calculates days remaining, urgency levels, and tracks completion accountability.
            </p>
          </div>
        </div>
      </div>

      {/* Recent Memories & Commitments Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Recent Memories */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-slate-100 flex items-center gap-2 text-sm sm:text-base">
              <Brain className="w-4 h-4 text-indigo-400" />
              Recent Organizational Memories
            </h2>
            <button
              onClick={() => setActiveTab("search-chat")}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
            >
              View All <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {memories.length === 0 ? (
            <div className="py-12 text-center text-slate-400 text-xs">
              No memories recorded yet. Ingest a document or audio recording to get started.
            </div>
          ) : (
            <div className="space-y-3">
              {memories.slice(0, 5).map((m) => (
                <div
                  key={m.id}
                  className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-slate-200 text-xs sm:text-sm line-clamp-1">
                      {m.title}
                    </span>
                    <span
                      className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                        m.memory_type === "decision"
                          ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                          : m.memory_type === "client_requirement"
                          ? "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                          : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                      }`}
                    >
                      {m.memory_type.replace("_", " ")}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2">{m.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Urgent & Upcoming Commitments */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-slate-100 flex items-center gap-2 text-sm sm:text-base">
              <CheckSquare className="w-4 h-4 text-emerald-400" />
              Action Items & Deadlines
            </h2>
            <button
              onClick={() => setActiveTab("tracker")}
              className="text-xs text-emerald-400 hover:text-emerald-300 font-medium flex items-center gap-1"
            >
              Open Tracker <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {commitments.length === 0 ? (
            <div className="py-12 text-center text-slate-400 text-xs">
              No commitments found for this organization.
            </div>
          ) : (
            <div className="space-y-3">
              {commitments.slice(0, 5).map((c) => (
                <div
                  key={c.id}
                  className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors flex items-start justify-between gap-3"
                >
                  <div>
                    <h4 className="font-semibold text-slate-200 text-xs sm:text-sm line-clamp-1">
                      {c.title}
                    </h4>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-1">{c.content}</p>
                    <div className="flex items-center gap-3 mt-2 text-[11px] text-slate-400">
                      {c.assignee && (
                        <span>
                          👤 <strong className="text-slate-300">{c.assignee}</strong>
                        </span>
                      )}
                      {c.deadline && (
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3 text-slate-500" />
                          {c.deadline}
                        </span>
                      )}
                    </div>
                  </div>

                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider shrink-0 ${
                      c.status === "OVERDUE"
                        ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                        : c.status === "COMPLETED"
                        ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                        : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                    }`}
                  >
                    {c.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
