"use client";

import React, { useState } from "react";
import {
  Search,
  MessageSquare,
  Bot,
  User,
  Send,
  Sparkles,
  Sliders,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FileText,
  Bookmark,
  Calendar,
} from "lucide-react";
import { api, ChatMessage, SearchResult } from "../lib/api";

interface SearchAndChatTabProps {
  companyId: string;
}

export const SearchAndChatTab: React.FC<SearchAndChatTabProps> = ({ companyId }) => {
  const [activeSubTab, setActiveSubTab] = useState<"chat" | "search">("chat");

  // Chat State
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Hello! I am your AFTERMIND AI Business Assistant. Ask me anything about historical decisions, client requirements, team commitments, or meeting discussions.",
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
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `⚠️ Error retrieving answer: ${err.message || "Failed to reach AI Assistant."}`,
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
      {/* Subtab Toggle */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold mb-1">
            <span>Module 3: Connected Long-Term Memory & RAG</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            AI Assistant & Semantic Vector Search
          </h2>
        </div>

        <div className="flex bg-slate-900 border border-slate-800 p-1 rounded-xl">
          <button
            onClick={() => setActiveSubTab("chat")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
              activeSubTab === "chat"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Bot className="w-3.5 h-3.5" />
            AI Assistant Chat
          </button>
          <button
            onClick={() => setActiveSubTab("search")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
              activeSubTab === "search"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Search className="w-3.5 h-3.5" />
            Semantic Search
          </button>
        </div>
      </div>

      {/* Mode 1: AI Chat Assistant */}
      {activeSubTab === "chat" && (
        <div className="glass-panel rounded-2xl border border-slate-800 flex flex-col h-[600px] overflow-hidden">
          {/* Chat Messages Log */}
          <div className="flex-1 p-5 overflow-y-auto space-y-4">
            {chatMessages.map((msg, i) => (
              <div
                key={i}
                className={`flex gap-3 text-xs sm:text-sm ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {msg.role === "assistant" && (
                  <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 flex items-center justify-center shrink-0">
                    <Bot className="w-4 h-4" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-2xl p-4 leading-relaxed ${
                    msg.role === "user"
                      ? "bg-indigo-600 text-white"
                      : "bg-slate-900/90 border border-slate-800 text-slate-200"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>

                  {/* Citations / Memory Sources */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-800 text-[11px] text-slate-400 space-y-1">
                      <span className="font-semibold text-slate-300 block">
                        Citations & Verified Sources:
                      </span>
                      {msg.citations.map((c, idx) => (
                        <div
                          key={idx}
                          className="flex items-center gap-2 p-1.5 rounded bg-slate-950/60 border border-slate-800/80"
                        >
                          <Bookmark className="w-3 h-3 text-indigo-400" />
                          <span className="font-medium text-slate-300 line-clamp-1">
                            {c.title}
                          </span>
                          <span className="text-slate-500">
                            ({c.memory_type?.replace("_", " ")})
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {msg.role === "user" && (
                  <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 flex items-center justify-center shrink-0">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))}
            {chatLoading && (
              <div className="flex gap-3 text-xs sm:text-sm justify-start">
                <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 text-slate-400 flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                  <span>Searching organizational memory & synthesizing answer...</span>
                </div>
              </div>
            )}
          </div>

          {/* Chat Input Bar */}
          <form
            onSubmit={handleSendMessage}
            className="p-4 border-t border-slate-800 bg-slate-950/70 flex gap-2 items-center"
          >
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask about historical decisions, commitments, deadlines..."
              className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-xs sm:text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
            <button
              type="submit"
              disabled={chatLoading || !chatInput.trim()}
              className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs sm:text-sm flex items-center gap-1.5 transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              <span className="hidden sm:inline">Ask AI</span>
            </button>
          </form>
        </div>
      )}

      {/* Mode 2: Vector Semantic Search */}
      {activeSubTab === "search" && (
        <div className="space-y-6">
          <form onSubmit={handleSearch} className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="w-4 h-4 absolute left-3.5 top-3.5 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Enter semantic query (e.g., 'database choice for production', 'sprint deadline')..."
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-10 pr-4 py-2.5 text-xs sm:text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <button
                type="submit"
                disabled={searchLoading || !searchQuery.trim()}
                className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs sm:text-sm flex items-center gap-2 transition-all disabled:opacity-50 shadow-md shadow-indigo-600/20"
              >
                {searchLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                <span>Search</span>
              </button>
            </div>

            {/* Threshold Slider */}
            <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
              <span className="flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-indigo-400" />
                Minimum Cosine Similarity:
              </span>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min="0.0"
                  max="0.8"
                  step="0.05"
                  value={similarityThreshold}
                  onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value))}
                  className="accent-indigo-500 cursor-pointer"
                />
                <span className="font-mono text-slate-300">{(similarityThreshold * 100).toFixed(0)}%</span>
              </div>
            </div>
          </form>

          {searchError && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{searchError}</span>
            </div>
          )}

          {/* Results List */}
          {searchResults && (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400 px-1">
                <span>Matching Memories ({searchResults.length})</span>
              </div>

              {searchResults.length === 0 ? (
                <div className="glass-panel p-10 rounded-2xl border border-slate-800 text-center text-xs text-slate-400">
                  No memories matched this query above {similarityThreshold * 100}% similarity threshold. Try lowering the threshold or refining your search.
                </div>
              ) : (
                searchResults.map((item, idx) => {
                  const m = item.memory || (item as any);
                  const sim = item.similarity ?? 0.85;
                  return (
                    <div
                      key={idx}
                      className="glass-card p-4 rounded-xl border border-slate-800 hover:border-indigo-500/40 transition-colors space-y-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="font-bold text-slate-100 text-sm">{m.title}</h4>
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/30">
                            {(sim * 100).toFixed(1)}% match
                          </span>
                          <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                            {m.memory_type?.replace("_", " ")}
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">{m.content}</p>
                      {item.source_title && (
                        <div className="text-[11px] text-slate-500 flex items-center gap-1.5 pt-1">
                          <FileText className="w-3 h-3" />
                          <span>Source: {item.source_title}</span>
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
