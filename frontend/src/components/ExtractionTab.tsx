"use client";

import React, { useState } from "react";
import {
  Cpu,
  Sparkles,
  Database,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Tag,
  Calendar,
  User,
  ArrowRight,
  BookmarkPlus,
} from "lucide-react";
import { api } from "../lib/api";

interface ExtractionTabProps {
  companyId: string;
  initialText?: string;
  initialTitle?: string;
  onRefreshMemories: () => void;
}

export const ExtractionTab: React.FC<ExtractionTabProps> = ({
  companyId,
  initialText = "",
  initialTitle = "",
  onRefreshMemories,
}) => {
  const [text, setText] = useState<string>(initialText);
  const [title, setTitle] = useState<string>(initialTitle || "Project Discussion / Meeting");
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<any | null>(null);
  const [storedSuccess, setStoredSuccess] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Update text when initialText prop changes from Ingestion tab
  React.useEffect(() => {
    if (initialText) setText(initialText);
    if (initialTitle) setTitle(initialTitle);
  }, [initialText, initialTitle]);

  const handleExtractOnly = async () => {
    if (!text.trim()) {
      setError("Please provide text to extract memories from.");
      return;
    }
    setLoading(true);
    setError(null);
    setStoredSuccess(false);

    try {
      const res = await api.extractMemories(text, title, companyId);
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Extraction failed");
    } finally {
      setLoading(false);
    }
  };

  const handleExtractAndStore = async () => {
    if (!text.trim()) {
      setError("Please provide text to extract and store.");
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await api.extractAndStore(text, title, companyId);
      setResult({ stored_count: res.stored_count, extraction_summary: res.extraction_summary });
      setStoredSuccess(true);
      onRefreshMemories();
    } catch (err: any) {
      setError(err.message || "Extraction and storage failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fadeIn">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs font-semibold mb-2">
          <span>Module 2: Intelligent Memory Extraction</span>
        </div>
        <h2 className="text-2xl font-bold text-white tracking-tight">
          Extract Decisions, Commitments & Action Items
        </h2>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Our AI model identifies actionable commitments, requirements, key decisions, and assigns deadlines and ownership.
        </p>
      </div>

      {/* Input Panel */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
            Document / Discussion Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Q3 Sprint Planning Meeting Notes"
            className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
            Raw Text / Discussion Transcript
          </label>
          <textarea
            rows={7}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste meeting transcript, client email, or document content here... (e.g. Srajan committed to finalize backend API by Friday. We decided to use PostgreSQL for production.)"
            className="w-full bg-slate-900 border border-slate-700 rounded-xl p-4 text-xs sm:text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500 font-mono"
          />
          <span className="text-[11px] text-slate-500 mt-1 block">
            {text.length} characters • {text.split(/\s+/).filter(Boolean).length} words
          </span>
        </div>

        {error && (
          <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3 pt-2">
          <button
            onClick={handleExtractOnly}
            disabled={loading || !text.trim()}
            className="flex-1 py-3 px-4 rounded-xl font-semibold text-xs sm:text-sm bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
            ) : (
              <Sparkles className="w-4 h-4 text-purple-400" />
            )}
            Preview Extraction
          </button>
          <button
            onClick={handleExtractAndStore}
            disabled={loading || !text.trim()}
            className="flex-1 py-3 px-4 rounded-xl font-semibold text-xs sm:text-sm bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white flex items-center justify-center gap-2 transition-all shadow-lg shadow-purple-600/25 disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin text-white" />
            ) : (
              <Database className="w-4 h-4 text-white" />
            )}
            Extract & Store in Long-Term Memory
          </button>
        </div>
      </div>

      {/* Success Banner if Stored */}
      {storedSuccess && (
        <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs sm:text-sm flex items-center justify-between gap-3 animate-fadeIn">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <span>
              Successfully extracted and indexed{" "}
              <strong>{result?.stored_count ?? 1} memories</strong> into Module 3 Vector Engine!
            </span>
          </div>
        </div>
      )}

      {/* Extraction Results Preview */}
      {result && result.memories && (
        <div className="glass-panel p-6 rounded-2xl border border-purple-500/30 space-y-5 animate-fadeIn">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white text-base flex items-center gap-2">
              <Cpu className="w-5 h-5 text-purple-400" />
              Extracted Memories ({result.memories.length})
            </h3>
            {result.source_summary && (
              <span className="text-xs text-slate-400 italic">
                Summary generated by AI
              </span>
            )}
          </div>

          {result.source_summary && (
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-300">
              <strong>Context Summary:</strong> {result.source_summary}
            </div>
          )}

          {/* Memory Items */}
          <div className="space-y-3">
            {result.memories.map((mem: any, idx: number) => (
              <div
                key={idx}
                className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-colors space-y-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <h4 className="font-bold text-slate-100 text-sm">{mem.title}</h4>
                  <span
                    className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                      mem.memory_type === "decision"
                        ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                        : mem.memory_type === "client_requirement"
                        ? "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                        : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                    }`}
                  >
                    {mem.memory_type.replace("_", " ")}
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">{mem.content}</p>

                {/* Metadata Chips: Assignee, Deadline, Confidence */}
                <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-slate-400">
                  {mem.assignee && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      <User className="w-3 h-3 text-indigo-400" />
                      {mem.assignee}
                    </span>
                  )}
                  {mem.deadline && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      <Calendar className="w-3 h-3 text-emerald-400" />
                      {mem.deadline}
                    </span>
                  )}
                  {mem.confidence && (
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                      Confidence: {(mem.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                  {mem.tags && mem.tags.length > 0 && (
                    <span className="inline-flex items-center gap-1 text-slate-500">
                      <Tag className="w-3 h-3" />
                      {mem.tags.join(", ")}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Extracted Entities */}
          {result.entities && result.entities.length > 0 && (
            <div className="pt-3 border-t border-slate-800">
              <label className="text-xs font-semibold text-slate-400 block mb-2">
                Recognized Business Entities:
              </label>
              <div className="flex flex-wrap gap-2">
                {result.entities.map((e: any, idx: number) => (
                  <span
                    key={idx}
                    className="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-slate-300"
                  >
                    <strong className="text-indigo-400">{e.name}</strong> ({e.entity_type})
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
