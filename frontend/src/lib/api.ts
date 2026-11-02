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
    formData.append("company_id", companyId);
    const res = await fetch(`${API_BASE_URL}/api/ingest/document?company_id=${encodeURIComponent(companyId)}`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Document ingestion failed" }));
      let msg = "Document ingestion failed";
      if (err?.detail) {
        msg = Array.isArray(err.detail)
          ? err.detail.map((d: any) => d.msg || (d.loc ? d.loc.join(".") : "") || JSON.stringify(d)).join(", ")
          : typeof err.detail === "object"
          ? JSON.stringify(err.detail)
          : String(err.detail);
      }
      throw new Error(msg);
    }
    const data = await res.json();
    const text = data.extracted_text || data.transcription || data.transcript || data.preview || "";
    return {
      ...data,
      extracted_text: text,
      transcription: text,
      transcript: text,
      preview: text,
      char_count: data.character_count ?? data.char_count ?? text.length,
      character_count: data.character_count ?? data.char_count ?? text.length,
    };
  },

  ingestAudio: async (file: File, companyId = "default-org", transcriber = "auto") => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("company_id", companyId);
    formData.append("transcriber", transcriber);
    const res = await fetch(
      `${API_BASE_URL}/api/ingest/audio?company_id=${encodeURIComponent(companyId)}&transcriber=${encodeURIComponent(transcriber)}`,
      {
        method: "POST",
        body: formData,
      }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Audio transcription failed" }));
      let msg = "Audio transcription failed";
      if (err?.detail) {
        msg = Array.isArray(err.detail)
          ? err.detail.map((d: any) => d.msg || (d.loc ? d.loc.join(".") : "") || JSON.stringify(d)).join(", ")
          : typeof err.detail === "object"
          ? JSON.stringify(err.detail)
          : String(err.detail);
      }
      throw new Error(msg);
    }
    const data = await res.json();
    const text = data.extracted_text || data.transcription || data.transcript || data.preview || "";
    return {
      ...data,
      extracted_text: text,
      transcription: text,
      transcript: text,
      preview: text,
      char_count: data.character_count ?? data.char_count ?? text.length,
      character_count: data.character_count ?? data.char_count ?? text.length,
    };
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
        extracted_text: text,
        text,
        title: title || "Executive Discussion",
        company_id: companyId || "default-org",
        source_id: sourceId || `src-${Date.now()}`,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Memory extraction failed" }));
      let msg = "Memory extraction failed";
      if (err?.detail) {
        msg = Array.isArray(err.detail)
          ? err.detail.map((d: any) => d.msg || (d.loc ? d.loc.join(".") : "") || JSON.stringify(d)).join(", ")
          : typeof err.detail === "object"
          ? JSON.stringify(err.detail)
          : String(err.detail);
      }
      throw new Error(msg);
    }
    return res.json();
  },

  extractAndStore: async (text: string, title?: string, companyId = "default-org") => {
    const res = await fetch(`${API_BASE_URL}/api/extraction/extract-and-store`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        extracted_text: text,
        text,
        source_title: title || "Executive Discussion",
        company_id: companyId || "default-org",
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Extraction and storage failed" }));
      let msg = "Extraction and storage failed";
      if (err?.detail) {
        msg = Array.isArray(err.detail)
          ? err.detail.map((d: any) => d.msg || (d.loc ? d.loc.join(".") : "") || JSON.stringify(d)).join(", ")
          : typeof err.detail === "object"
          ? JSON.stringify(err.detail)
          : String(err.detail);
      }
      throw new Error(msg);
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
    const payload = JSON.stringify({
      question: query,
      query: query,
      company_id: companyId,
      conversation_history: history,
    });

    const doFetch = async () => {
      return fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payload,
      });
    };

    let res: Response;
    try {
      res = await doFetch();
    } catch (netErr: any) {
      // Retry once after 2 seconds in case backend is spinning up
      await new Promise((resolve) => setTimeout(resolve, 2000));
      try {
        res = await doFetch();
      } catch {
        throw new Error("Could not connect to backend server. If using Render free tier, the backend may take 30-50s to wake up from sleep. Please try again.");
      }
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Assistant chat failed" }));
      let msg = "Assistant chat failed";
      if (err?.detail) {
        msg = Array.isArray(err.detail)
          ? err.detail.map((d: any) => d.msg || (d.loc ? d.loc.join(".") : "") || JSON.stringify(d)).join(", ")
          : typeof err.detail === "object"
          ? JSON.stringify(err.detail)
          : String(err.detail);
      }
      throw new Error(msg);
    }
    return res.json();
  },

  // Module 4: Commitment & Decision Tracker
  getCommitments: async (companyId = "default-org", status?: string) => {
    const url = new URL(`${API_BASE_URL}/api/tracker/commitments`);
    url.searchParams.set("company_id", companyId);
    if (status && status !== "ALL") {
      url.searchParams.set("status", status.toLowerCase());
    }
    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch commitments");
    const data = await res.json();
    return (data || []).map((c: any) => {
      const daysLeft = c.days_left ?? c.days_remaining;
      const rawStatus = (c.tracker_status || c.memory_status || c.status || "PENDING").toUpperCase();
      let urgency: CommitmentItem["urgency_level"] = "NORMAL";
      if (daysLeft !== undefined && daysLeft < 0) urgency = "CRITICAL";
      else if (daysLeft !== undefined && daysLeft <= 3) urgency = "HIGH";

      return {
        id: c.memory_id || c.id,
        company_id: c.company_id,
        title: c.title,
        content: c.description || c.content,
        assignee: c.owner || c.assignee || "Unassigned",
        deadline: c.deadline ? String(c.deadline) : (c.deadline_text || undefined),
        status: rawStatus === "DUE_SOON" ? "PENDING" : rawStatus,
        urgency_level: urgency,
        days_remaining: daysLeft,
        confidence: c.confidence ?? 0.95,
        created_at: c.created_at,
        source_title: c.source_title
      };
    });
  },

  getTrackerAnalytics: async (companyId = "default-org") => {
    let res = await fetch(`${API_BASE_URL}/api/tracker/summary?company_id=${encodeURIComponent(companyId)}`, {
      cache: "no-store",
    });
    if (!res.ok) {
      res = await fetch(`${API_BASE_URL}/api/tracker/analytics?company_id=${encodeURIComponent(companyId)}`, {
        cache: "no-store",
      });
    }
    if (!res.ok) throw new Error("Failed to fetch tracker analytics");
    const data = await res.json();
    const total = data.total ?? (data.total_open !== undefined ? data.total_open + (data.completed || 0) : 0);
    const active = data.active ?? data.total_open ?? 0;
    const completed = data.completed ?? 0;
    const completion_rate = data.completion_rate ?? (total > 0 ? Math.round((completed / total) * 100) : 0);
    return {
      total,
      active,
      overdue: data.overdue ?? 0,
      due_soon: data.due_soon ?? 0,
      pending: data.pending ?? 0,
      completed,
      completion_rate
    };
  },

  updateCommitmentStatus: async (memoryId: string, status: string, notes?: string) => {
    const res = await fetch(`${API_BASE_URL}/api/tracker/commitments/${memoryId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_id: "default-org", status, notes }),
    });
    if (!res.ok) throw new Error("Failed to update status");
    return res.json();
  },
};
