"use client";

import React, { useState } from "react";
import {
  CheckSquare,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  User,
  Filter,
  RefreshCw,
  Loader2,
  ArrowLeft,
} from "lucide-react";
import { api, CommitmentItem } from "../lib/api";

interface CommitmentTrackerTabProps {
  companyId: string;
  commitments: CommitmentItem[];
  analytics: any;
  loading: boolean;
  onRefresh: () => void;
  onBack?: () => void;
}

export const CommitmentTrackerTab: React.FC<CommitmentTrackerTabProps> = ({
  companyId,
  commitments,
  analytics,
  loading,
  onRefresh,
  onBack,
}) => {
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const handleMarkComplete = async (id: string) => {
    setUpdatingId(id);
    try {
      await api.updateCommitmentStatus(id, "COMPLETED", "Marked complete from dashboard");
      onRefresh();
    } catch (err: any) {
      alert("Failed to update status: " + err.message);
    } finally {
      setUpdatingId(null);
    }
  };

  const filteredCommitments = commitments.filter((c) => {
    if (statusFilter === "ALL") return true;
    return c.status === statusFilter;
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-fadeIn">
      {/* Back to Dashboard Button */}
      {onBack && (
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-600 text-sm font-semibold transition-all hover:-translate-x-0.5 shadow-sm"
        >
          <ArrowLeft className="w-4 h-4 text-blue-400" />
          <span>Back to Dashboard</span>
        </button>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded bg-emerald-950 border border-emerald-600 text-emerald-300 text-xs font-bold uppercase tracking-wider mb-1">
            <span>Module 4: Smart Commitment & Decision Tracker</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Commitments, Deadlines & Accountability
          </h2>
          <p className="text-sm sm:text-base text-slate-200 mt-1 leading-relaxed">
            Tracks business tasks, owners, deadlines, and urgency levels with real-time countdowns.
          </p>
        </div>

        <button
          onClick={onRefresh}
          className="self-start sm:self-auto px-4 py-2.5 rounded-lg bg-slate-900 border border-slate-600 hover:border-slate-500 text-slate-100 text-sm font-semibold flex items-center gap-2 transition-all hover:scale-105"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Data</span>
        </button>
      </div>

      {/* Analytics Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl biz-card border border-slate-700">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300">Total Tracked</span>
          <div className="text-3xl font-extrabold text-white mt-2">
            {analytics.total ?? commitments.length}
          </div>
        </div>
        <div className="p-5 rounded-xl biz-card border border-slate-700">
          <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">Active Tasks</span>
          <div className="text-3xl font-extrabold text-emerald-400 mt-2">
            {analytics.active ?? commitments.filter((c) => c.status === "ACTIVE").length}
          </div>
        </div>
        <div className="p-5 rounded-xl biz-card border border-slate-700">
          <span className="text-xs font-bold uppercase tracking-wider text-rose-400">Overdue / Critical</span>
          <div className="text-3xl font-extrabold text-rose-400 mt-2">
            {analytics.overdue ?? commitments.filter((c) => c.status === "OVERDUE").length}
          </div>
        </div>
        <div className="p-5 rounded-xl biz-card border border-slate-700">
          <span className="text-xs font-bold uppercase tracking-wider text-blue-400">Completion Rate</span>
          <div className="text-3xl font-extrabold text-blue-300 mt-2">
            {analytics.completion_rate ?? 0}%
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-2.5 border-b border-slate-700 pb-3">
        <Filter className="w-4 h-4 text-slate-300 mr-1" />
        {["ALL", "ACTIVE", "PENDING", "COMPLETED", "OVERDUE"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-4 py-2 rounded-lg text-xs sm:text-sm font-bold transition-all ${
              statusFilter === s
                ? "bg-blue-600 text-white shadow-sm"
                : "bg-slate-900 border border-slate-700 text-slate-300 hover:text-white"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Commitment Cards */}
      {filteredCommitments.length === 0 ? (
        <div className="biz-panel p-12 rounded-xl border border-slate-700 text-center text-sm text-slate-300">
          No commitments found under status "{statusFilter}". You can extract commitments from meeting notes in Module 2!
        </div>
      ) : (
        <div className="space-y-4">
          {filteredCommitments.map((c) => {
            const isOverdue = c.status === "OVERDUE" || (c.days_remaining !== undefined && c.days_remaining < 0);
            const isCompleted = c.status === "COMPLETED";

            return (
              <div
                key={c.id}
                className={`biz-panel p-5 sm:p-6 rounded-xl border transition-all ${
                  isOverdue
                    ? "border-rose-500 bg-rose-950/20"
                    : isCompleted
                    ? "border-emerald-600/70 bg-emerald-950/20 opacity-80"
                    : "border-slate-700 hover:border-blue-500 bg-[#161f30]"
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <h3
                        className={`font-bold text-base sm:text-lg ${
                          isCompleted ? "line-through text-slate-400" : "text-white"
                        }`}
                      >
                        {c.title}
                      </h3>

                      {/* Status Badge */}
                      <span
                        className={`text-[11px] font-bold uppercase px-2.5 py-0.5 rounded ${
                          isOverdue
                            ? "bg-rose-900/60 text-rose-200 border border-rose-500"
                            : isCompleted
                            ? "bg-emerald-900/60 text-emerald-200 border border-emerald-500"
                            : "bg-blue-900/60 text-blue-200 border border-blue-500"
                        }`}
                      >
                        {c.status}
                      </span>

                      {/* Urgency Badge */}
                      {c.urgency_level && (
                        <span
                          className={`text-[11px] font-bold uppercase px-2.5 py-0.5 rounded ${
                            c.urgency_level === "CRITICAL"
                              ? "bg-rose-600 text-white font-extrabold animate-pulse"
                              : c.urgency_level === "HIGH"
                              ? "bg-amber-600/40 text-amber-200 border border-amber-500 font-bold"
                              : "bg-slate-800 text-slate-300 border border-slate-700"
                          }`}
                        >
                          {c.urgency_level}
                        </span>
                      )}
                    </div>

                    <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-normal">{c.content}</p>

                    {/* Metadata: Assignee, Deadline, Days Remaining */}
                    <div className="flex flex-wrap items-center gap-5 pt-2 text-xs sm:text-sm text-slate-300">
                      {c.assignee && (
                        <span className="flex items-center gap-1.5">
                          <User className="w-4 h-4 text-blue-400" />
                          <span>
                            Assignee: <strong className="text-white">{c.assignee}</strong>
                          </span>
                        </span>
                      )}
                      {c.deadline && (
                        <span className="flex items-center gap-1.5">
                          <Calendar className="w-4 h-4 text-slate-400" />
                          <span>
                            Deadline: <strong className="text-white">{c.deadline}</strong>
                          </span>
                        </span>
                      )}
                      {c.days_remaining !== undefined && !isCompleted && (
                        <span
                          className={`flex items-center gap-1.5 font-bold ${
                            c.days_remaining < 0
                              ? "text-rose-400"
                              : c.days_remaining <= 2
                              ? "text-amber-400"
                              : "text-emerald-400"
                          }`}
                        >
                          <Clock className="w-4 h-4" />
                          {c.days_remaining < 0
                            ? `Overdue by ${Math.abs(c.days_remaining)} days`
                            : c.days_remaining === 0
                            ? "Due Today"
                            : `${c.days_remaining} days remaining`}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Complete Button */}
                  {!isCompleted && (
                    <button
                      onClick={() => handleMarkComplete(c.id)}
                      disabled={updatingId === c.id}
                      className="shrink-0 px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-emerald-600 hover:border-emerald-500 border border-slate-600 text-slate-200 hover:text-white text-xs sm:text-sm font-bold flex items-center gap-2 transition-all shadow-sm"
                    >
                      {updatingId === c.id ? (
                        <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
                      ) : (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      )}
                      <span>Mark Complete</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
