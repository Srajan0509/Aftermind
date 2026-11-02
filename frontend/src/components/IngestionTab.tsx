"use client";

import React, { useState } from "react";
import {
  UploadCloud,
  FileText,
  Mic,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
} from "lucide-react";
import { api } from "../lib/api";

interface IngestionTabProps {
  companyId: string;
  onSendToExtraction: (text: string, title: string) => void;
  onBack?: () => void;
}

export const IngestionTab: React.FC<IngestionTabProps> = ({
  companyId,
  onSendToExtraction,
  onBack,
}) => {
  const [ingestionMode, setIngestionMode] = useState<"document" | "audio">("document");
  const [file, setFile] = useState<File | null>(null);
  const [transcriber, setTranscriber] = useState<string>("auto");
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [localTextFallback, setLocalTextFallback] = useState<string>("");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      setError(null);
      setResult(null);
      setLocalTextFallback("");
      if (selected.name.toLowerCase().endsWith(".txt")) {
        selected.text().then((txt) => {
          setLocalTextFallback(txt);
        }).catch(() => {});
      }
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
        if (!res.extracted_text && localTextFallback) {
          res.extracted_text = localTextFallback;
          res.transcription = localTextFallback;
          res.transcript = localTextFallback;
          res.preview = localTextFallback;
        }
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
          <span>Module 1: Multi-Source AI Data Ingestion</span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          Ingest Business Documents & Meeting Recordings
        </h2>
        <p className="text-sm sm:text-base text-slate-200 mt-1 leading-relaxed">
          Upload PDF reports, Word documents, text files, or meeting audio to parse content and transcribe speech using AI.
        </p>
      </div>

      {/* Mode Switcher */}
      <div className="flex border-b border-slate-700 gap-8">
        <button
          onClick={() => {
            setIngestionMode("document");
            setFile(null);
            setResult(null);
            setError(null);
          }}
          className={`pb-3 font-bold text-sm sm:text-base flex items-center gap-2.5 transition-colors relative ${
            ingestionMode === "document"
              ? "text-blue-400 border-b-2 border-blue-500"
              : "text-slate-400 hover:text-white"
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
          className={`pb-3 font-bold text-sm sm:text-base flex items-center gap-2.5 transition-colors relative ${
            ingestionMode === "audio"
              ? "text-blue-400 border-b-2 border-blue-500"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <Mic className="w-4 h-4" />
          Audio Recordings (MP3, WAV, M4A)
        </button>
      </div>

      {/* Ingestion Form */}
      <form onSubmit={handleIngest} className="biz-panel p-6 sm:p-7 rounded-xl border border-slate-700 space-y-6">
        {/* Upload Zone */}
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-200 mb-2.5">
            Select {ingestionMode === "document" ? "Document" : "Audio"} File
          </label>
          <div className="relative border-2 border-dashed border-slate-600 hover:border-blue-400 rounded-xl p-8 sm:p-10 text-center transition-colors bg-slate-900/90 cursor-pointer">
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
            <div className="flex flex-col items-center justify-center space-y-3">
              <div className="w-14 h-14 rounded-full bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center">
                <UploadCloud className="w-7 h-7" />
              </div>
              <p className="text-sm sm:text-base font-semibold text-white">
                {file ? (
                  <span className="text-blue-400">{file.name}</span>
                ) : (
                  <>
                    <span className="text-blue-400 underline underline-offset-4">Click to browse</span> or drag & drop file here
                  </>
                )}
              </p>
              <p className="text-xs sm:text-sm text-slate-300">
                {ingestionMode === "document"
                  ? "Supported formats: PDF, DOCX, TXT (up to 50MB)"
                  : "Supported audio: MP3, WAV, M4A (transcribed with Whisper/Gemini)"}
              </p>
              {file && (
                <span className="text-xs text-slate-300 font-mono">
                  File Size: {(file.size / 1024 / 1024).toFixed(2)} MB
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Audio Transcriber Selection */}
        {ingestionMode === "audio" && (
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-200 mb-2">
              AI Transcription Engine
            </label>
            <select
              value={transcriber}
              onChange={(e) => setTranscriber(e.target.value)}
              className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-2.5 text-sm text-white font-medium focus:outline-none focus:border-blue-500 cursor-pointer"
            >
              <option value="auto">Auto (Detects best available: Whisper / Gemini)</option>
              <option value="whisper">OpenAI Whisper (High-accuracy enterprise transcription)</option>
              <option value="gemini">Google Gemini 2.0 Audio (Multimodal reasoning)</option>
              <option value="mock">Mock Transcriber (Local fast testing without API key)</option>
            </select>
          </div>
        )}

        {error && (
          <div className="p-4 rounded-lg bg-rose-950/80 border border-rose-500 text-rose-200 text-sm flex items-center gap-2.5">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading || !file}
          className={`w-full py-3.5 rounded-lg font-bold text-sm sm:text-base flex items-center justify-center gap-2.5 transition-all shadow-md ${
            loading || !file
              ? "bg-slate-800 text-slate-400 cursor-not-allowed border border-slate-700"
              : "bg-blue-600 hover:bg-blue-500 text-white shadow-blue-600/30 hover:scale-[1.01]"
          }`}
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Processing & Parsing Content...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              <span>
                {ingestionMode === "document" ? "Extract Document Content" : "Transcribe Meeting Audio"}
              </span>
            </>
          )}
        </button>
      </form>

      {/* Ingestion Results Preview */}
      {result && (
        <div className="biz-panel p-6 sm:p-7 rounded-xl border border-blue-500 bg-slate-900 space-y-5 animate-fadeIn">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="w-6 h-6 text-emerald-400" />
              <h3 className="font-bold text-white text-base sm:text-lg">
                {ingestionMode === "document" ? "Document Ingested Successfully" : "Audio Transcribed Successfully"}
              </h3>
            </div>
            <span className="text-xs px-3 py-1 rounded-full bg-emerald-950 text-emerald-200 border border-emerald-600 font-bold">
              ID: {result.source_id?.slice(0, 8)}...
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs sm:text-sm">
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 block text-xs">Title</span>
              <span className="font-bold text-white line-clamp-1">{result.title}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 block text-xs">Word Count</span>
              <span className="font-bold text-white">{result.word_count ?? 0}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 block text-xs">Char Count</span>
              <span className="font-bold text-white">{result.character_count ?? result.char_count ?? (result.extracted_text?.length || localTextFallback?.length || 0)}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 block text-xs">Source Type</span>
              <span className="font-bold text-blue-300 uppercase">{result.source_type}</span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">
              Extracted Content Preview:
            </label>
            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 text-xs sm:text-sm text-slate-200 max-h-56 overflow-y-auto font-mono whitespace-pre-wrap leading-relaxed">
              {result.extracted_text || result.transcription || result.transcript || result.preview || localTextFallback || "No content preview available."}
            </div>
          </div>

          {/* Direct CTA to Next Module */}
          <div className="pt-3 border-t border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <p className="text-xs sm:text-sm text-slate-300">
              Next step: extract business decisions, commitments, and deadlines from this content.
            </p>
            <button
              onClick={() => {
                const text = result.extracted_text || result.transcription || result.transcript || result.preview || localTextFallback || "";
                onSendToExtraction(text, result.title || file?.name || "Ingested Document");
              }}
              className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs sm:text-sm flex items-center gap-2 shadow-md shadow-blue-600/30"
            >
              <span>Send to Module 2 (Extraction)</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
