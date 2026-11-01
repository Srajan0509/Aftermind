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
      {/* Executive Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-blue-950 to-slate-900 border border-slate-700 p-6 sm:p-8 shadow-xl">
        <div className="relative z-10 max-w-4xl">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-md bg-blue-500/20 border border-blue-400/40 text-blue-200 text-xs sm:text-sm font-semibold mb-3">
            <Sparkles className="w-4 h-4 text-blue-300" />
            <span>AI-Powered Executive Memory & Decision Intelligence</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight leading-snug">
            Don't Just Store Information. <br />
            <span className="text-blue-400">Remember, Understand and Act on It.</span>
          </h1>
          <p className="mt-3 text-sm sm:text-base text-slate-200 leading-relaxed max-w-3xl">
            AFTERMIND unifies executive discussions, client specifications, and meeting transcripts into connected corporate intelligence. Prevent missed deadlines, review historical decisions, and query with verified AI assistance.
          </p>

          <div className="mt-6 flex flex-wrap gap-3.5">
            <button
              onClick={() => setActiveTab("ingestion")}
              className="inline-flex items-center gap-2.5 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm shadow-md shadow-blue-600/30 transition-all hover:scale-[1.02]"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Ingest Document or Audio</span>
            </button>
            <button
              onClick={() => setActiveTab("search-chat")}
              className="inline-flex items-center gap-2.5 px-5 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-600 font-semibold text-sm transition-all hover:scale-[1.02]"
            >
              <Search className="w-4 h-4 text-blue-400" />
              <span>Ask AI Memory Assistant</span>
            </button>
            <button
              onClick={() => setActiveTab("tracker")}
              className="inline-flex items-center gap-2.5 px-5 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-600 font-semibold text-sm transition-all hover:scale-[1.02]"
            >
              <CheckSquare className="w-4 h-4 text-emerald-400" />
              <span>Track Commitments & Deadlines</span>
            </button>
          </div>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Memories */}
        <div className="biz-card p-5 rounded-xl border border-slate-700 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Total Business Memories
            </span>
            <div className="w-9 h-9 rounded-lg bg-blue-600/20 text-blue-400 flex items-center justify-center border border-blue-500/30">
              <Brain className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">
              {loading ? "..." : memories.length}
            </span>
            <span className="text-xs text-blue-300 font-medium">Stored Entities</span>
          </div>
          <div className="mt-2 text-xs font-medium text-slate-300 flex items-center gap-2">
            <span>{decisions.length} Decisions</span>
            <span>•</span>
            <span>{requirements.length} Requirements</span>
          </div>
        </div>

        {/* Active Commitments */}
        <div className="biz-card p-5 rounded-xl border border-slate-700 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Active Commitments
            </span>
            <div className="w-9 h-9 rounded-lg bg-emerald-600/20 text-emerald-400 flex items-center justify-center border border-emerald-500/30">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-emerald-400">
              {loading ? "..." : activeCount}
            </span>
            <span className="text-xs text-emerald-300 font-medium">In Progress</span>
          </div>
          <div className="mt-2 text-xs font-medium text-slate-300">
            Completion rate: <strong className="text-white">{analytics.completion_rate ?? 0}%</strong>
          </div>
        </div>

        {/* Overdue Alerts */}
        <div className="biz-card p-5 rounded-xl border border-slate-700 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Overdue / Critical
            </span>
            <div
              className={`w-9 h-9 rounded-lg flex items-center justify-center border ${
                overdueCount > 0
                  ? "bg-rose-950/80 text-rose-300 border-rose-500"
                  : "bg-slate-800 text-slate-400 border-slate-700"
              }`}
            >
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span
              className={`text-3xl font-extrabold ${
                overdueCount > 0 ? "text-rose-400" : "text-white"
              }`}
            >
              {loading ? "..." : overdueCount}
            </span>
            <span className="text-xs text-slate-300 font-medium">Action Items</span>
          </div>
          <div className="mt-2 text-xs font-medium text-slate-300">
            {overdueCount > 0 ? (
              <span className="text-rose-300 font-semibold">Immediate follow-up required</span>
            ) : (
              "All deliverables on schedule"
            )}
          </div>
        </div>

        {/* Vector Intelligence Engine */}
        <div className="biz-card p-5 rounded-xl border border-slate-700 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Vector Intelligence
            </span>
            <div className="w-9 h-9 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center border border-indigo-500/30">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-blue-200">1536</span>
            <span className="text-xs text-blue-300 font-medium">Dim Vectors</span>
          </div>
          <div className="mt-2 text-xs font-medium text-slate-300">
            Multi-LLM & Hybrid RAG Active
          </div>
        </div>
      </div>

      {/* Module Flow Pipeline Cards */}
      <div>
        <h2 className="text-lg sm:text-xl font-bold text-white mb-4 flex items-center gap-2">
          <Layers className="w-5 h-5 text-blue-400" />
          End-to-End Intelligence Pipeline
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div
            onClick={() => setActiveTab("ingestion")}
            className="p-5 rounded-xl biz-card border border-slate-700 hover:border-blue-500 cursor-pointer group"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-blue-400 uppercase tracking-wider">
                Module 1
              </span>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-400 group-hover:translate-x-1 transition-all" />
            </div>
            <h3 className="font-bold text-base text-white mt-2">Data Ingestion</h3>
            <p className="text-xs sm:text-sm text-slate-300 mt-1 leading-relaxed">
              Extract text from PDF, DOCX, TXT, or transcribe MP3, WAV, M4A audio.
            </p>
          </div>

          <div
            onClick={() => setActiveTab("extraction")}
            className="p-5 rounded-xl biz-card border border-slate-700 hover:border-blue-500 cursor-pointer group"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-blue-400 uppercase tracking-wider">
                Module 2
              </span>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-400 group-hover:translate-x-1 transition-all" />
            </div>
            <h3 className="font-bold text-base text-white mt-2">Memory Extraction</h3>
            <p className="text-xs sm:text-sm text-slate-300 mt-1 leading-relaxed">
              AI parses decisions, commitments, requirements, entities, and confidence scores.
            </p>
          </div>

          <div
            onClick={() => setActiveTab("search-chat")}
            className="p-5 rounded-xl biz-card border border-slate-700 hover:border-blue-500 cursor-pointer group"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-blue-400 uppercase tracking-wider">
                Module 3
              </span>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-400 group-hover:translate-x-1 transition-all" />
            </div>
            <h3 className="font-bold text-base text-white mt-2">Connected Memory & RAG</h3>
            <p className="text-xs sm:text-sm text-slate-300 mt-1 leading-relaxed">
              Vector semantic search and conversational assistant with verifiable source citations.
            </p>
          </div>

          <div
            onClick={() => setActiveTab("tracker")}
            className="p-5 rounded-xl biz-card border border-slate-700 hover:border-blue-500 cursor-pointer group"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                Module 4
              </span>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-400 group-hover:translate-x-1 transition-all" />
            </div>
            <h3 className="font-bold text-base text-white mt-2">Commitment Tracker</h3>
            <p className="text-xs sm:text-sm text-slate-300 mt-1 leading-relaxed">
              Tracks days remaining, urgency levels, and team accountability.
            </p>
          </div>
        </div>
      </div>

      {/* Recent Activity Split */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Recent Memories */}
        <div className="biz-panel p-6 rounded-xl border border-slate-700">
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-800">
            <h2 className="font-bold text-white flex items-center gap-2 text-base sm:text-lg">
              <Brain className="w-5 h-5 text-blue-400" />
              Recent Organizational Memories
            </h2>
            <button
              onClick={() => setActiveTab("search-chat")}
              className="text-xs sm:text-sm text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1"
            >
              View All <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {memories.length === 0 ? (
            <div className="py-12 text-center text-slate-400 text-sm">
              No memories recorded yet. Ingest a document or audio recording to get started.
            </div>
          ) : (
            <div className="space-y-3">
              {memories.slice(0, 5).map((m) => (
                <div
                  key={m.id}
                  className="p-4 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-slate-100 text-sm line-clamp-1">
                      {m.title}
                    </span>
                    <span
                      className={`text-[11px] uppercase font-bold px-2.5 py-0.5 rounded ${
                        m.memory_type === "decision"
                          ? "bg-purple-900/40 text-purple-200 border border-purple-700/50"
                          : m.memory_type === "client_requirement"
                          ? "bg-blue-900/40 text-blue-200 border border-blue-700/50"
                          : "bg-emerald-900/40 text-emerald-200 border border-emerald-700/50"
                      }`}
                    >
                      {m.memory_type.replace("_", " ")}
                    </span>
                  </div>
                  <p className="text-xs sm:text-sm text-slate-300 mt-1.5 leading-relaxed line-clamp-2">
                    {m.content}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Urgent & Upcoming Commitments */}
        <div className="biz-panel p-6 rounded-xl border border-slate-700">
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-800">
            <h2 className="font-bold text-white flex items-center gap-2 text-base sm:text-lg">
              <CheckSquare className="w-5 h-5 text-emerald-400" />
              Action Items & Deadlines
            </h2>
            <button
              onClick={() => setActiveTab("tracker")}
              className="text-xs sm:text-sm text-emerald-400 hover:text-emerald-300 font-semibold flex items-center gap-1"
            >
              Open Tracker <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {commitments.length === 0 ? (
            <div className="py-12 text-center text-slate-400 text-sm">
              No commitments found for this organization.
            </div>
          ) : (
            <div className="space-y-3">
              {commitments.slice(0, 5).map((c) => (
                <div
                  key={c.id}
                  className="p-4 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 transition-colors flex items-start justify-between gap-3"
                >
                  <div>
                    <h4 className="font-semibold text-slate-100 text-sm line-clamp-1">
                      {c.title}
                    </h4>
                    <p className="text-xs sm:text-sm text-slate-300 mt-1 line-clamp-1">
                      {c.content}
                    </p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-slate-300">
                      {c.assignee && (
                        <span>
                          👤 <strong className="text-white">{c.assignee}</strong>
                        </span>
                      )}
                      {c.deadline && (
                        <span className="flex items-center gap-1 text-slate-300">
                          <Calendar className="w-3.5 h-3.5 text-slate-400" />
                          {c.deadline}
                        </span>
                      )}
                    </div>
                  </div>

                  <span
                    className={`text-[11px] font-bold px-2.5 py-0.5 rounded uppercase tracking-wider shrink-0 ${
                      c.status === "OVERDUE"
                        ? "bg-rose-900/50 text-rose-200 border border-rose-600"
                        : c.status === "COMPLETED"
                        ? "bg-emerald-900/50 text-emerald-200 border border-emerald-600"
                        : "bg-amber-900/50 text-amber-200 border border-amber-600"
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
