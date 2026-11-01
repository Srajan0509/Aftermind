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
} from "lucide-react";
import { api, CommitmentItem } from "../lib/api";

interface CommitmentTrackerTabProps {
  companyId: string;
  commitments: CommitmentItem[];
  analytics: any;
  loading: boolean;
  onRefresh: () => void;
}

export const CommitmentTrackerTab: React.FC<CommitmentTrackerTabProps> = ({
  companyId,
  commitments,
  analytics,
  loading,
  onRefresh,
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
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold mb-1">
            <span>Module 4: Smart Commitment & Decision Tracker</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Commitments, Deadlines & Accountability
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Tracks business tasks, owners, deadlines, and urgency levels with real-time countdowns.
          </p>
        </div>

        <button
          onClick={onRefresh}
          className="self-start sm:self-auto px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700 hover:border-slate-600 text-slate-300 text-xs font-medium flex items-center gap-2 transition-all hover:scale-105"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Analytics Mini-Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl glass-card border border-slate-800">
          <span className="text-xs text-slate-400 font-medium">Total Tracked</span>
          <div className="text-2xl font-extrabold text-white mt-1">
            {analytics.total ?? commitments.length}
          </div>
        </div>
        <div className="p-4 rounded-xl glass-card border border-slate-800">
          <span className="text-xs text-emerald-400 font-medium">Active Tasks</span>
          <div className="text-2xl font-extrabold text-emerald-400 mt-1">
            {analytics.active ?? commitments.filter((c) => c.status === "ACTIVE").length}
          </div>
        </div>
        <div className="p-4 rounded-xl glass-card border border-slate-800">
          <span className="text-xs text-rose-400 font-medium">Overdue / Critical</span>
          <div className="text-2xl font-extrabold text-rose-400 mt-1">
            {analytics.overdue ?? commitments.filter((c) => c.status === "OVERDUE").length}
          </div>
        </div>
        <div className="p-4 rounded-xl glass-card border border-slate-800">
          <span className="text-xs text-indigo-400 font-medium">Completion Rate</span>
          <div className="text-2xl font-extrabold text-indigo-300 mt-1">
            {analytics.completion_rate ?? 0}%
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-3">
        <Filter className="w-4 h-4 text-slate-400 mr-1" />
        {["ALL", "ACTIVE", "PENDING", "COMPLETED", "OVERDUE"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              statusFilter === s
                ? "bg-indigo-600 text-white shadow-sm"
                : "bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Commitment Cards */}
      {filteredCommitments.length === 0 ? (
        <div className="glass-panel p-12 rounded-2xl border border-slate-800 text-center text-xs text-slate-400">
          No commitments found under "{statusFilter}". You can extract commitments from meeting notes in Module 2!
        </div>
      ) : (
        <div className="space-y-3">
          {filteredCommitments.map((c) => {
            const isOverdue = c.status === "OVERDUE" || (c.days_remaining !== undefined && c.days_remaining < 0);
            const isCompleted = c.status === "COMPLETED";

            return (
              <div
                key={c.id}
                className={`glass-panel p-5 rounded-2xl border transition-all ${
                  isOverdue
                    ? "border-rose-500/30 bg-rose-950/10"
                    : isCompleted
                    ? "border-emerald-500/30 bg-emerald-950/10 opacity-75"
                    : "border-slate-800 hover:border-slate-700 bg-slate-900/60"
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3
                        className={`font-bold text-sm sm:text-base ${
                          isCompleted ? "line-through text-slate-400" : "text-white"
                        }`}
                      >
                        {c.title}
                      </h3>

                      {/* Status Badge */}
                      <span
                        className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                          isOverdue
                            ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                            : isCompleted
                            ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                            : "bg-blue-500/20 text-blue-300 border border-blue-500/40"
                        }`}
                      >
                        {c.status}
                      </span>

                      {/* Urgency Badge */}
                      {c.urgency_level && (
                        <span
                          className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                            c.urgency_level === "CRITICAL"
                              ? "bg-rose-600/30 text-rose-200 border border-rose-500 animate-pulse"
                              : c.urgency_level === "HIGH"
                              ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                              : "bg-slate-800 text-slate-400"
                          }`}
                        >
                          {c.urgency_level}
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed">{c.content}</p>

                    {/* Metadata: Assignee, Deadline, Days Remaining */}
                    <div className="flex flex-wrap items-center gap-4 pt-2 text-xs text-slate-400">
                      {c.assignee && (
                        <span className="flex items-center gap-1.5">
                          <User className="w-3.5 h-3.5 text-indigo-400" />
                          <span>
                            Assignee: <strong className="text-slate-200">{c.assignee}</strong>
                          </span>
                        </span>
                      )}
                      {c.deadline && (
                        <span className="flex items-center gap-1.5">
                          <Calendar className="w-3.5 h-3.5 text-slate-400" />
                          <span>
                            Deadline: <strong className="text-slate-200">{c.deadline}</strong>
                          </span>
                        </span>
                      )}
                      {c.days_remaining !== undefined && !isCompleted && (
                        <span
                          className={`flex items-center gap-1.5 font-semibold ${
                            c.days_remaining < 0
                              ? "text-rose-400"
                              : c.days_remaining <= 2
                              ? "text-amber-400"
                              : "text-emerald-400"
                          }`}
                        >
                          <Clock className="w-3.5 h-3.5" />
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
                      className="shrink-0 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-emerald-600/20 hover:border-emerald-500/40 border border-slate-700 text-slate-300 hover:text-emerald-300 text-xs font-semibold flex items-center gap-1.5 transition-all"
                    >
                      {updatingId === c.id ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                      ) : (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
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
