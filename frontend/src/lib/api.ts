/**
 * AFTERMIND Unified API Client
 * Connects frontend to all 4 backend modules:
 * - Module 1: Ingestion (/api/ingest/*)
 * - Module 2: Extraction (/api/extraction/*)
 * - Module 3: Long-term Memory & Search/Chat (/api/memories, /api/search, /api/chat)
 * - Module 4: Commitment Tracker (/api/tracker/*)
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Company {
  id: string;
  name: string;
  domain?: string;
  created_at: string;
}

export interface Memory {
  id: string;
  company_id: string;
  project_id?: string;
  source_id?: string;
  memory_type: "decision" | "client_requirement" | "employee_commitment" | "important_deadline" | "meeting_discussion" | "general_info";
  title: string;
  content: string;
  status: "active" | "superseded" | "modified" | "completed" | "cancelled";
  confidence: number;
  tags?: string[];
  meta_info?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export interface CommitmentItem {
  id: string;
  company_id: string;
  title: string;
  content: string;
  assignee?: string;
  deadline?: string;
  status: "ACTIVE" | "PENDING" | "COMPLETED" | "OVERDUE" | "CANCELLED";
  urgency_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NORMAL" | "OVERDUE";
  days_remaining?: number;
  confidence: number;
  source_title?: string;
  created_at: string;
}

export interface SearchResult {
  memory: Memory;
  similarity: number;
  source_title?: string;
  source_type?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Array<{
    title: string;
    source_title?: string;
    memory_type: string;
    confidence?: number;
  }>;
}

export const api = {
  // Health
  checkHealth: async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/`, { cache: "no-store" });
      if (!res.ok) return { online: false };
      const data = await res.json();
      return { online: true, ...data };
    } catch {
      return { online: false };
    }
  },

  // Module 1: Data Ingestion
  ingestDocument: async (file: File, companyId = "default-org") => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE_URL}/api/ingest/document?company_id=${encodeURIComponent(companyId)}`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Document ingestion failed" }));
      throw new Error(err.detail || "Document ingestion failed");
    }
    return res.json();
  },

  ingestAudio: async (file: File, companyId = "default-org", transcriber = "auto") => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(
      `${API_BASE_URL}/api/ingest/audio?company_id=${encodeURIComponent(companyId)}&transcriber=${encodeURIComponent(transcriber)}`,
      {
        method: "POST",
        body: formData,
      }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Audio transcription failed" }));
      throw new Error(err.detail || "Audio transcription failed");
    }
    return res.json();
  },

  getSupportedFormats: async () => {
    const res = await fetch(`${API_BASE_URL}/api/ingest/formats`);
    return res.json();
  },

  // Module 2: Memory Extraction
  extractMemories: async (text: string, title?: string, companyId = "default-org", sourceId?: string) => {
    const res = await fetch(`${API_BASE_URL}/api/extraction/extract`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        title: title || "Ingested Document",
        company_id: companyId,
        source_id: sourceId,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Memory extraction failed" }));
      throw new Error(err.detail || "Memory extraction failed");
    }
    return res.json();
  },

  extractAndStore: async (text: string, title?: string, companyId = "default-org") => {
    const res = await fetch(`${API_BASE_URL}/api/extraction/extract-and-store`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        source_title: title || "Ingested Document",
        company_id: companyId,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Extraction and storage failed" }));
      throw new Error(err.detail || "Extraction and storage failed");
    }
    return res.json();
  },

  // Module 3: Long-term Memory & Search / Chat
  getMemories: async (companyId = "default-org", limit = 50, memoryType?: string) => {
    const url = new URL(`${API_BASE_URL}/api/memories`);
    url.searchParams.set("company_id", companyId);
    url.searchParams.set("limit", limit.toString());
    if (memoryType && memoryType !== "all") {
      url.searchParams.set("memory_type", memoryType);
    }
    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch memories");
    return res.json();
  },

  getCompanies: async () => {
    const res = await fetch(`${API_BASE_URL}/api/companies`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  },

  createCompany: async (name: string, domain?: string) => {
    const res = await fetch(`${API_BASE_URL}/api/companies`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, domain }),
    });
    if (!res.ok) throw new Error("Failed to create company");
    return res.json();
  },

  semanticSearch: async (query: string, companyId = "default-org", limit = 10, threshold = 0.1) => {
    const res = await fetch(`${API_BASE_URL}/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        company_id: companyId,
        limit,
        threshold,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Search failed" }));
      throw new Error(err.detail || "Search failed");
    }
    return res.json();
  },

  chatWithMemory: async (query: string, companyId = "default-org", history: Array<{ role: string; content: string }> = []) => {
    const res = await fetch(`${API_BASE_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        company_id: companyId,
        conversation_history: history,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Assistant chat failed" }));
      throw new Error(err.detail || "Assistant chat failed");
    }
    return res.json();
  },

  // Module 4: Commitment & Decision Tracker
  getCommitments: async (companyId = "default-org", status?: string) => {
    const url = new URL(`${API_BASE_URL}/api/tracker/commitments`);
    url.searchParams.set("company_id", companyId);
    if (status && status !== "ALL") {
      url.searchParams.set("status", status);
    }
    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch commitments");
    return res.json();
  },

  getTrackerAnalytics: async (companyId = "default-org") => {
    const res = await fetch(`${API_BASE_URL}/api/tracker/analytics?company_id=${encodeURIComponent(companyId)}`, {
      cache: "no-store",
    });
    if (!res.ok) throw new Error("Failed to fetch tracker analytics");
    return res.json();
  },

  updateCommitmentStatus: async (memoryId: string, status: string, notes?: string) => {
    const res = await fetch(`${API_BASE_URL}/api/tracker/commitments/${memoryId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status, notes }),
    });
    if (!res.ok) throw new Error("Failed to update status");
    return res.json();
  },
};
