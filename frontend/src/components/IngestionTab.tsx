"use client";

import React, { useState } from "react";
import {
  UploadCloud,
  FileText,
  Mic,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
  Info,
} from "lucide-react";
import { api } from "../lib/api";

interface IngestionTabProps {
  companyId: string;
  onSendToExtraction: (text: string, title: string) => void;
}

export const IngestionTab: React.FC<IngestionTabProps> = ({
  companyId,
  onSendToExtraction,
}) => {
  const [ingestionMode, setIngestionMode] = useState<"document" | "audio">("document");
  const [file, setFile] = useState<File | null>(null);
  const [transcriber, setTranscriber] = useState<string>("auto");
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      setResult(null);
    }
  };

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a file to ingest.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      if (ingestionMode === "document") {
        const res = await api.ingestDocument(file, companyId);
        setResult(res);
      } else {
        const res = await api.ingestAudio(file, companyId, transcriber);
        setResult(res);
      }
    } catch (err: any) {
      setError(err.message || "Failed to process file.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fadeIn">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold mb-2">
          <span>Module 1: Multi-Source AI Data Ingestion</span>
        </div>
        <h2 className="text-2xl font-bold text-white tracking-tight">
          Ingest Business Documents & Meeting Recordings
        </h2>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Upload PDF reports, Word documents, text files, or meeting audio to parse content and transcribe speech using AI.
        </p>
      </div>

      {/* Mode Switcher */}
      <div className="flex border-b border-slate-800 gap-6">
        <button
          onClick={() => {
            setIngestionMode("document");
            setFile(null);
            setResult(null);
            setError(null);
          }}
          className={`pb-3 font-semibold text-sm flex items-center gap-2 transition-colors relative ${
            ingestionMode === "document"
              ? "text-indigo-400 border-b-2 border-indigo-500"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <FileText className="w-4 h-4" />
          Documents (PDF, DOCX, TXT)
        </button>
        <button
          onClick={() => {
            setIngestionMode("audio");
            setFile(null);
            setResult(null);
            setError(null);
          }}
          className={`pb-3 font-semibold text-sm flex items-center gap-2 transition-colors relative ${
            ingestionMode === "audio"
              ? "text-indigo-400 border-b-2 border-indigo-500"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Mic className="w-4 h-4" />
          Audio Recordings (MP3, WAV, M4A)
        </button>
      </div>

      {/* Ingestion Form */}
      <form onSubmit={handleIngest} className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-5">
        {/* Upload Zone */}
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
            Select {ingestionMode === "document" ? "Document" : "Audio"} File
          </label>
          <div className="relative border-2 border-dashed border-slate-700 hover:border-indigo-500/60 rounded-xl p-8 text-center transition-colors bg-slate-900/40 cursor-pointer">
            <input
              type="file"
              accept={
                ingestionMode === "document"
                  ? ".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
                  : ".mp3,.wav,.m4a,audio/mpeg,audio/wav,audio/x-m4a,audio/mp4"
              }
              onChange={handleFileChange}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="flex flex-col items-center justify-center space-y-2">
              <div className="w-12 h-12 rounded-full bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                <UploadCloud className="w-6 h-6" />
              </div>
              <p className="text-sm font-medium text-slate-200">
                {file ? (
                  <span className="text-indigo-400 font-semibold">{file.name}</span>
                ) : (
                  <>
                    <span className="text-indigo-400 hover:underline">Click to upload</span> or drag and drop
                  </>
                )}
              </p>
              <p className="text-xs text-slate-400">
                {ingestionMode === "document"
                  ? "Supported formats: PDF, DOCX, TXT (up to 50MB)"
                  : "Supported audio: MP3, WAV, M4A (transcribed with Whisper/Gemini)"}
              </p>
              {file && (
                <span className="text-[11px] text-slate-400">
                  Size: {(file.size / 1024 / 1024).toFixed(2)} MB
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Audio Transcriber Selection */}
        {ingestionMode === "audio" && (
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
              AI Transcription Engine
            </label>
            <select
              value={transcriber}
              onChange={(e) => setTranscriber(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="auto">Auto (Detects best available: Whisper / Gemini)</option>
              <option value="whisper">OpenAI Whisper (High-accuracy transcription)</option>
              <option value="gemini">Google Gemini 2.0 Audio (Multimodal reasoning)</option>
              <option value="mock">Mock Transcriber (Local fast testing without API key)</option>
            </select>
          </div>
        )}

        {error && (
          <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading || !file}
          className={`w-full py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition-all shadow-lg ${
            loading || !file
              ? "bg-slate-800 text-slate-500 cursor-not-allowed"
              : "bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/30 hover:scale-[1.01]"
          }`}
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Processing & Parsing Content...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              <span>
                {ingestionMode === "document" ? "Extract Document Content" : "Transcribe Meeting Audio"}
              </span>
            </>
          )}
        </button>
      </form>

      {/* Ingestion Results Preview */}
      {result && (
        <div className="glass-panel p-6 rounded-2xl border border-indigo-500/30 bg-slate-900/80 space-y-4 animate-fadeIn">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <h3 className="font-bold text-white text-base">
                {ingestionMode === "document" ? "Document Ingested Successfully" : "Audio Transcribed Successfully"}
              </h3>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-medium">
              Source ID: {result.source_id?.slice(0, 8)}...
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400 block">Title</span>
              <span className="font-semibold text-slate-200 line-clamp-1">{result.title}</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400 block">Word Count</span>
              <span className="font-semibold text-slate-200">{result.word_count ?? 0}</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400 block">Char Count</span>
              <span className="font-semibold text-slate-200">{result.char_count ?? 0}</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400 block">Type</span>
              <span className="font-semibold text-indigo-300 uppercase">{result.source_type}</span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1">
              Extracted Content Preview:
            </label>
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 max-h-48 overflow-y-auto font-mono whitespace-pre-wrap">
              {result.transcription || result.preview || "No content preview available."}
            </div>
          </div>

          {/* Direct CTA to Next Module */}
          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
            <p className="text-xs text-slate-400">
              Proceed to extract business decisions and commitments from this content.
            </p>
            <button
              onClick={() => {
                const text = result.transcription || result.preview || "";
                onSendToExtraction(text, result.title || "Ingested Document");
              }}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-medium text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/20"
            >
              <span>Send to Module 2 (Extraction)</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
