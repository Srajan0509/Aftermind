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
  ArrowLeft,
} from "lucide-react";
import { api } from "../lib/api";

interface ExtractionTabProps {
  companyId: string;
  initialText?: string;
  initialTitle?: string;
  onRefreshMemories: () => void;
  onBack?: () => void;
}

export const ExtractionTab: React.FC<ExtractionTabProps> = ({
  companyId,
  initialText = "",
  initialTitle = "",
  onRefreshMemories,
  onBack,
}) => {
  const [text, setText] = useState<string>(initialText);
  const [title, setTitle] = useState<string>(initialTitle || "Executive Discussion / Meeting");
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<any | null>(null);
  const [storedSuccess, setStoredSuccess] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

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
      setResult(res);
      setStoredSuccess(true);
      onRefreshMemories();
    } catch (err: any) {
      setError(err.message || "Extraction and storage failed");
    } finally {
      setLoading(false);
    }
  };

  const loadSampleMeeting = () => {
    setTitle("AFTERMIND Executive Board & Product Strategy Meeting");
    setText(`AFTERMIND EXECUTIVE BOARD & PRODUCT STRATEGY MEETING
Date: November 1, 2026
Attendees: Sarah Jenkins (VP Product), David Miller (Chief Architect), Srajan Shetty (Lead Backend Engineer), Nirmal Yadav (Frontend Lead), Amrita Sharma (AI Ingestion Specialist)
Organization: Acme Global Technologies (default-org)

1. EXECUTIVE SUMMARY & STRATEGIC OVERVIEW
The leadership team met to review the Q4 release roadmap for the enterprise decision intelligence platform. The primary goal is reducing organizational knowledge loss and tracking cross-functional commitments across engineering and product teams.

2. ARCHITECTURAL & STRATEGIC DECISIONS
- Decision 1 (Database Architecture): The architecture team officially decided to use PostgreSQL with pgvector hosted on Supabase for production rather than self-hosted vector databases, ensuring ACID compliance and automated backups.
- Decision 2 (Authentication Standard): The board approved mandating OAuth 2.0 with Okta and Google Enterprise SSO for all customer tenants starting in Q1 2027.
- Decision 3 (Model Selection): The AI committee decided to utilize Google Gemini 2.0 Flash as the default multimodal reasoning engine, with Groq LLaMA-3.3-70B configured as the ultra-low latency fallback.

3. CLIENT REQUIREMENTS (ACME FINANCIAL GROUP)
- Requirement 1: Acme Financial requires end-to-end data encryption at rest (AES-256) and automated SOC-2 compliance audit logging for every memory query.
- Requirement 2: The mobile client must support real-time audio voice-note ingestion in MP3 and M4A formats with transcription accuracy exceeding 95%.
- Requirement 3: Multi-tenant data segregation must be strictly enforced at the database row level using company_id tenant filters.

4. ASSIGNED COMMITMENTS & CRITICAL DEADLINES
- Commitment 1: Srajan committed to finalizing all backend REST API endpoints and PostgreSQL pgvector integration by November 8, 2026. (Assignee: Srajan Shetty, Priority: CRITICAL)
- Commitment 2: Nirmal committed to delivering the executive dashboard and commitment tracking UI by November 12, 2026. (Assignee: Nirmal Yadav, Priority: HIGH)
- Commitment 3: Amrita committed to completing document parsers for PDF and DOCX multi-source ingestion with automatic Whisper fallback by November 6, 2026. (Assignee: Amrita Sharma, Priority: HIGH)
- Commitment 4: David Miller committed to performing security penetration testing and load testing up to 10,000 concurrent requests by November 18, 2026. (Assignee: David Miller, Priority: MEDIUM)`);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fadeIn">
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
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded bg-blue-950 border border-blue-600 text-blue-300 text-xs font-bold uppercase tracking-wider mb-2">
          <span>Module 2: Intelligent Memory Extraction</span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          Extract Decisions, Commitments & Action Items
        </h2>
        <p className="text-sm sm:text-base text-slate-200 mt-1 leading-relaxed">
          AI identifies corporate commitments, client specifications, key decisions, and maps ownership and deadlines.
        </p>
      </div>

      {/* Input Panel */}
      <div className="biz-panel p-6 sm:p-7 rounded-xl border border-slate-700 space-y-5">
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-200 mb-2">
            Document / Discussion Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Q3 Executive Strategy & Sprint Planning"
            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-3 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 font-medium"
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-200">
              Raw Text / Discussion Transcript
            </label>
            <button
              type="button"
              onClick={loadSampleMeeting}
              className="text-xs text-blue-400 hover:text-blue-300 font-bold underline underline-offset-4 flex items-center gap-1.5 cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5 text-blue-400" />
              <span>Load Sample Meeting Data</span>
            </button>
          </div>
          <textarea
            rows={8}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste meeting transcript, client requirements, or document notes here... (e.g. Srajan committed to finalize backend API by Friday. We decided to use PostgreSQL for production.)"
            className="w-full bg-slate-900 border border-slate-600 rounded-lg p-4 text-xs sm:text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:border-blue-500 font-mono leading-relaxed"
          />
          <span className="text-xs text-slate-400 mt-1.5 block">
            {text.length} characters • {text.split(/\s+/).filter(Boolean).length} words
          </span>
        </div>

        {error && (
          <div className="p-4 rounded-lg bg-rose-950/80 border border-rose-500 text-rose-200 text-sm flex items-center gap-2.5">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3.5 pt-2">
          <button
            onClick={handleExtractOnly}
            disabled={loading || !text.trim()}
            className="flex-1 py-3 px-5 rounded-lg font-bold text-sm bg-slate-800 hover:bg-slate-700 text-white border border-slate-600 flex items-center justify-center gap-2.5 transition-all disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
            ) : (
              <Sparkles className="w-4 h-4 text-blue-400" />
            )}
            <span>Preview Extraction Only</span>
          </button>
          <button
            onClick={handleExtractAndStore}
            disabled={loading || !text.trim()}
            className="flex-1 py-3 px-5 rounded-lg font-bold text-sm bg-blue-600 hover:bg-blue-500 text-white flex items-center justify-center gap-2.5 transition-all shadow-md shadow-blue-600/30 disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin text-white" />
            ) : (
              <Database className="w-4 h-4 text-white" />
            )}
            <span>Extract & Store in Long-Term Memory</span>
          </button>
        </div>
      </div>

      {/* Success Banner if Stored */}
      {storedSuccess && (
        <div className="p-4 rounded-xl bg-emerald-950 border border-emerald-600 text-emerald-200 text-sm font-medium flex items-center justify-between gap-3 animate-fadeIn">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
            <span>
              Successfully extracted and indexed{" "}
              <strong className="text-white">{result?.stored_count ?? 1} business memories</strong> into the Vector Memory Engine!
            </span>
          </div>
        </div>
      )}

      {/* Extraction Results Preview */}
      {result && result.memories && (
        <div className="biz-panel p-6 sm:p-7 rounded-xl border border-blue-500 space-y-5 animate-fadeIn">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white text-base sm:text-lg flex items-center gap-2.5">
              <Cpu className="w-5 h-5 text-blue-400" />
              Extracted Memories ({result.memories.length})
            </h3>
            {result.source_summary && (
              <span className="text-xs text-slate-300 font-medium">
                Verified Executive Summary
              </span>
            )}
          </div>

          {result.source_summary && (
            <div className="p-4 rounded-lg bg-slate-900 border border-slate-700 text-xs sm:text-sm text-slate-200 leading-relaxed">
              <strong className="text-white">Context Summary:</strong> {result.source_summary}
            </div>
          )}

          {/* Memory Items */}
          <div className="space-y-3.5">
            {result.memories.map((mem: any, idx: number) => (
              <div
                key={idx}
                className="p-4 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 transition-colors space-y-2.5"
              >
                <div className="flex items-center justify-between gap-2">
                  <h4 className="font-bold text-white text-sm sm:text-base">{mem.title}</h4>
                  <span
                    className={`text-[11px] font-bold uppercase px-2.5 py-0.5 rounded ${
                      mem.memory_type === "decision"
                        ? "bg-purple-900/40 text-purple-200 border border-purple-700"
                        : mem.memory_type === "client_requirement"
                        ? "bg-blue-900/40 text-blue-200 border border-blue-700"
                        : "bg-emerald-900/40 text-emerald-200 border border-emerald-700"
                    }`}
                  >
                    {mem.memory_type.replace("_", " ")}
                  </span>
                </div>

                <p className="text-xs sm:text-sm text-slate-200 leading-relaxed">{mem.content}</p>

                {/* Metadata Chips: Assignee, Deadline, Confidence */}
                <div className="flex flex-wrap items-center gap-3 pt-1 text-xs text-slate-300">
                  {mem.assignee && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 text-white font-medium">
                      <User className="w-3.5 h-3.5 text-blue-400" />
                      {mem.assignee}
                    </span>
                  )}
                  {mem.deadline && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 text-white font-medium">
                      <Calendar className="w-3.5 h-3.5 text-emerald-400" />
                      {mem.deadline}
                    </span>
                  )}
                  {mem.confidence && (
                    <span className="px-2.5 py-1 rounded bg-slate-800 text-slate-300 font-mono">
                      Confidence: {(mem.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                  {mem.tags && mem.tags.length > 0 && (
                    <span className="inline-flex items-center gap-1.5 text-slate-400">
                      <Tag className="w-3.5 h-3.5" />
                      {mem.tags.join(", ")}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Extracted Entities */}
          {result.entities && result.entities.length > 0 && (
            <div className="pt-4 border-t border-slate-800">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-300 block mb-2.5">
                Recognized Business Entities:
              </label>
              <div className="flex flex-wrap gap-2">
                {result.entities.map((e: any, idx: number) => (
                  <span
                    key={idx}
                    className="px-3 py-1 rounded-md bg-slate-800 border border-slate-700 text-xs text-white"
                  >
                    <strong className="text-blue-400">{e.name}</strong> ({e.entity_type})
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
