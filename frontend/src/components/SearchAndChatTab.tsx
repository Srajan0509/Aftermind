"use client";

import React, { useState } from "react";
import {
  Search,
  Bot,
  User,
  Send,
  Sliders,
  AlertCircle,
  Loader2,
  FileText,
  Bookmark,
  ArrowLeft,
} from "lucide-react";
import { api, ChatMessage, SearchResult } from "../lib/api";

interface SearchAndChatTabProps {
  companyId: string;
  onBack?: () => void;
}

export const SearchAndChatTab: React.FC<SearchAndChatTabProps> = ({ companyId, onBack }) => {
  const [activeSubTab, setActiveSubTab] = useState<"chat" | "search">("chat");

  // Chat State
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Hello! I am your AFTERMIND AI Business Assistant. Ask me anything regarding historical organizational decisions, client specifications, team commitments, or meeting discussions.",
    },
  ]);
  const [chatInput, setChatInput] = useState<string>("");
  const [chatLoading, setChatLoading] = useState<boolean>(false);

  // Search State
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [similarityThreshold, setSimilarityThreshold] = useState<number>(0.1);
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searchLoading, setSearchLoading] = useState<boolean>(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Handle Chat
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading) return;

    const userQuery = chatInput.trim();
    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "user", content: userQuery }]);
    setChatLoading(true);

    try {
      const history = chatMessages.map((m) => ({ role: m.role, content: m.content }));
      const response = await api.chatWithMemory(userQuery, companyId, history);

      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.answer || response.response || "No response received.",
          citations: response.sources || response.citations || [],
        },
      ]);
    } catch (err: any) {
      // Safely extract a readable message from any thrown value
      const errMsg =
        err instanceof Error
          ? err.message
          : typeof err === "string"
          ? err
          : err?.message || err?.detail || JSON.stringify(err) || "Failed to reach AI Assistant.";
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `⚠️ Error retrieving answer: ${errMsg}`,
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  // Handle Semantic Search
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim() || searchLoading) return;

    setSearchLoading(true);
    setSearchError(null);

    try {
      const res = await api.semanticSearch(searchQuery.trim(), companyId, 10, similarityThreshold);
      setSearchResults(res.results || res || []);
    } catch (err: any) {
      setSearchError(err.message || "Search failed");
    } finally {
      setSearchLoading(false);
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

      {/* Subtab Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-700 pb-3 gap-3">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded bg-blue-950 border border-blue-600 text-blue-300 text-xs font-bold uppercase tracking-wider mb-1">
            <span>Module 3: Connected Long-Term Memory & RAG</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
            AI Assistant & Semantic Vector Search
          </h2>
        </div>

        <div className="flex bg-slate-900 border border-slate-700 p-1 rounded-lg">
          <button
            onClick={() => setActiveSubTab("chat")}
            className={`px-4 py-2 rounded-md text-xs sm:text-sm font-bold flex items-center gap-2 transition-all ${
              activeSubTab === "chat"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-300 hover:text-white"
            }`}
          >
            <Bot className="w-4 h-4" />
            AI Assistant Chat
          </button>
          <button
            onClick={() => setActiveSubTab("search")}
            className={`px-4 py-2 rounded-md text-xs sm:text-sm font-bold flex items-center gap-2 transition-all ${
              activeSubTab === "search"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-300 hover:text-white"
            }`}
          >
            <Search className="w-4 h-4" />
            Semantic Search
          </button>
        </div>
      </div>

      {/* Mode 1: AI Chat Assistant */}
      {activeSubTab === "chat" && (
        <div className="biz-panel rounded-xl border border-slate-700 flex flex-col h-[620px] overflow-hidden">
          {/* Chat Messages Log */}
          <div className="flex-1 p-5 sm:p-6 overflow-y-auto space-y-4">
            {chatMessages.map((msg, i) => (
              <div
                key={i}
                className={`flex gap-3 text-sm sm:text-base ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {msg.role === "assistant" && (
                  <div className="w-9 h-9 rounded-lg bg-blue-600/20 border border-blue-500/40 text-blue-400 flex items-center justify-center shrink-0">
                    <Bot className="w-5 h-5" />
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-xl p-4 sm:p-5 leading-relaxed ${
                    msg.role === "user"
                      ? "bg-blue-600 text-white font-medium"
                      : "bg-slate-900 border border-slate-700 text-slate-100"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>

                  {/* Citations / Memory Sources */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-slate-800 text-xs text-slate-300 space-y-1.5">
                      <span className="font-bold text-white block">
                        Citations & Verified Corporate Sources:
                      </span>
                      {msg.citations.map((c, idx) => (
                        <div
                          key={idx}
                          className="flex items-center gap-2 p-2 rounded bg-slate-950 border border-slate-800"
                        >
                          <Bookmark className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                          <span className="font-semibold text-white line-clamp-1">
                            {c.title}
                          </span>
                          <span className="text-slate-400">
                            ({c.memory_type?.replace("_", " ")})
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {msg.role === "user" && (
                  <div className="w-9 h-9 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 flex items-center justify-center shrink-0">
                    <User className="w-5 h-5" />
                  </div>
                )}
              </div>
            ))}
            {chatLoading && (
              <div className="flex gap-3 text-sm justify-start">
                <div className="w-9 h-9 rounded-lg bg-blue-600/20 border border-blue-500/40 text-blue-400 flex items-center justify-center shrink-0">
                  <Bot className="w-5 h-5" />
                </div>
                <div className="p-4 rounded-xl bg-slate-900 border border-slate-700 text-slate-200 flex items-center gap-2.5">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                  <span>Searching organizational memory & synthesizing answer...</span>
                </div>
              </div>
            )}
          </div>

          {/* Chat Input Bar */}
          <form
            onSubmit={handleSendMessage}
            className="p-4 border-t border-slate-700 bg-slate-900 flex gap-2.5 items-center"
          >
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask about historical decisions, commitments, deadlines..."
              className="flex-1 bg-slate-950 border border-slate-600 rounded-lg px-4 py-3 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 font-medium"
            />
            <button
              type="submit"
              disabled={chatLoading || !chatInput.trim()}
              className="px-5 py-3 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm flex items-center gap-2 transition-all shadow-md shadow-blue-600/30 disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              <span>Ask AI</span>
            </button>
          </form>
        </div>
      )}

      {/* Mode 2: Vector Semantic Search */}
      {activeSubTab === "search" && (
        <div className="space-y-6">
          <form onSubmit={handleSearch} className="biz-panel p-6 rounded-xl border border-slate-700 space-y-4">
            <div className="flex gap-2.5">
              <div className="relative flex-1">
                <Search className="w-5 h-5 absolute left-3.5 top-3.5 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Enter semantic query (e.g., 'database choice for production', 'sprint deadline')..."
                  className="w-full bg-slate-900 border border-slate-600 rounded-lg pl-11 pr-4 py-3 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 font-medium"
                />
              </div>
              <button
                type="submit"
                disabled={searchLoading || !searchQuery.trim()}
                className="px-6 py-3 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm flex items-center gap-2 transition-all disabled:opacity-50 shadow-md shadow-blue-600/30"
              >
                {searchLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                <span>Search</span>
              </button>
            </div>

            {/* Threshold Slider */}
            <div className="flex items-center justify-between text-xs sm:text-sm text-slate-200 pt-1 font-medium">
              <span className="flex items-center gap-1.5">
                <Sliders className="w-4 h-4 text-blue-400" />
                Minimum Cosine Similarity:
              </span>
              <div className="flex items-center gap-2.5">
                <input
                  type="range"
                  min="0.0"
                  max="0.8"
                  step="0.05"
                  value={similarityThreshold}
                  onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value))}
                  className="accent-blue-500 cursor-pointer"
                />
                <span className="font-mono text-white font-bold">{(similarityThreshold * 100).toFixed(0)}%</span>
              </div>
            </div>
          </form>

          {searchError && (
            <div className="p-4 rounded-lg bg-rose-950/80 border border-rose-500 text-rose-200 text-sm flex items-center gap-2.5">
              <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
              <span>{searchError}</span>
            </div>
          )}

          {/* Results List */}
          {searchResults && (
            <div className="space-y-3.5">
              <div className="flex items-center justify-between text-xs sm:text-sm text-slate-300 px-1 font-semibold">
                <span>Matching Memories ({searchResults.length})</span>
              </div>

              {searchResults.length === 0 ? (
                <div className="biz-panel p-10 rounded-xl border border-slate-700 text-center text-sm text-slate-300">
                  No memories matched this query above {(similarityThreshold * 100).toFixed(0)}% similarity threshold. Try adjusting the slider or your search terms.
                </div>
              ) : (
                searchResults.map((item, idx) => {
                  const m = item.memory || (item as any);
                  const sim = item.similarity ?? 0.85;
                  return (
                    <div
                      key={idx}
                      className="biz-card p-5 rounded-xl border border-slate-700 hover:border-blue-500 transition-colors space-y-2.5"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="font-bold text-white text-base">{m.title}</h4>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-blue-950 text-blue-300 border border-blue-600">
                            {(sim * 100).toFixed(1)}% match
                          </span>
                          <span className="text-xs font-bold uppercase px-2.5 py-1 rounded bg-slate-800 text-slate-200 border border-slate-700">
                            {m.memory_type?.replace("_", " ")}
                          </span>
                        </div>
                      </div>
                      <p className="text-sm text-slate-200 leading-relaxed">{m.content}</p>
                      {item.source_title && (
                        <div className="text-xs text-slate-400 flex items-center gap-1.5 pt-1">
                          <FileText className="w-3.5 h-3.5" />
                          <span>Source: <strong className="text-slate-300">{item.source_title}</strong></span>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
