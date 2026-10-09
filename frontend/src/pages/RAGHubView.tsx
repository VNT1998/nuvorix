import React, { useState, useEffect } from "react";
import { KnowledgeBase, KnowledgeDocument, RetrievalChunk } from "../types";
import { api } from "../lib/api";
import { BookOpen, Upload, Search, FileText, Sparkles } from "lucide-react";

interface RAGHubViewProps {
  knowledgeBases: KnowledgeBase[];
  selectedProjectId: string;
  onRefreshKBs: () => Promise<void>;
}

export const RAGHubView: React.FC<RAGHubViewProps> = ({
  knowledgeBases,
  selectedProjectId,
  onRefreshKBs,
}) => {
  const [selectedKBId, setSelectedKBId] = useState(knowledgeBases[0]?.id || "");
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);

  // Ingest form state
  const [docTitle, setDocTitle] = useState("");
  const [docSource, setDocSource] = useState("docs/spec.md");
  const [docContent, setDocContent] = useState("");
  const [ingesting, setIngesting] = useState(false);

  // Query state
  const [queryText, setQueryText] = useState("What are the release gate and rollback policies?");
  const [queryResults, setQueryResults] = useState<RetrievalChunk[]>([]);
  const [searching, setSearching] = useState(false);

  const loadDocuments = async (kbId: string) => {
    try {
      const docs = await api.getDocuments(kbId);
      setDocuments(docs);
    } catch (_) {}
  };

  useEffect(() => {
    if (selectedKBId) {
      loadDocuments(selectedKBId);
    }
  }, [selectedKBId]);

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedKBId || !docTitle || !docContent) return;
    setIngesting(true);
    try {
      await api.ingestDocument(selectedKBId, docTitle, docContent, docSource);
      setDocTitle("");
      setDocContent("");
      await loadDocuments(selectedKBId);
      alert("Document indexed successfully!");
    } catch (err: any) {
      alert(`Ingestion failed: ${err.message}`);
    } finally {
      setIngesting(false);
    }
  };

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedKBId || !queryText.trim()) return;
    setSearching(true);
    try {
      const res = await api.queryKnowledge(selectedKBId, queryText, 4);
      setQueryResults(res.results);
    } catch (err: any) {
      alert(`Query failed: ${err.message}`);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-blue-600" />
          RAG Platform & Semantic Knowledge Retrieval
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Ingest unstructured documentation, compute dense normalized embeddings, chunk passages, and perform vector similarity queries with source attribution.
        </p>
      </div>

      {/* Select KB */}
      <div className="flex items-center gap-3 p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
        <span className="text-xs font-medium text-slate-700">Active Knowledge Base:</span>
        <select
          value={selectedKBId}
          onChange={(e) => setSelectedKBId(e.target.value)}
          className="bg-white border border-slate-300 text-xs rounded-lg px-3 py-1.5 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs cursor-pointer"
        >
          {knowledgeBases.map((kb) => (
            <option key={kb.id} value={kb.id}>
              {kb.name} ({kb.embedding_model})
            </option>
          ))}
        </select>
      </div>

      {/* Two Column Layout: Document Ingestion & Query Tester */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Ingest Documents */}
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
              <Upload className="w-4 h-4 text-blue-600" />
              Ingest Document & Build Vector Index
            </h2>
            <span className="text-[11px] font-semibold text-slate-500">{documents.length} Indexed Docs</span>
          </div>

          <form onSubmit={handleIngest} className="space-y-3 text-xs">
            <div>
              <label className="block text-slate-700 font-medium mb-1">Document Title</label>
              <input
                type="text"
                required
                value={docTitle}
                onChange={(e) => setDocTitle(e.target.value)}
                placeholder="e.g. Distributed Consensus Runbook"
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs"
              />
            </div>
            <div>
              <label className="block text-slate-700 font-medium mb-1">Source URI</label>
              <input
                type="text"
                value={docSource}
                onChange={(e) => setDocSource(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs font-mono text-[11px]"
              />
            </div>
            <div>
              <label className="block text-slate-700 font-medium mb-1">Content (Markdown or Plain Text)</label>
              <textarea
                required
                value={docContent}
                onChange={(e) => setDocContent(e.target.value)}
                placeholder="Paste engineering documentation, release specifications, or incident procedures..."
                rows={5}
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs font-mono text-[11px]"
              />
            </div>
            <button
              type="submit"
              disabled={ingesting || !selectedKBId}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold shadow-xs flex items-center justify-center gap-2 cursor-pointer transition-all disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5" />
              {ingesting ? "Chunking & Generating Embeddings..." : "Index Document"}
            </button>
          </form>

          {/* List of existing indexed documents */}
          <div className="pt-2 border-t border-slate-200 space-y-2">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              Currently Indexed Documents
            </span>
            <div className="max-h-40 overflow-y-auto space-y-1.5">
              {documents.map((d) => (
                <div
                  key={d.id}
                  className="p-2.5 rounded bg-slate-50 border border-slate-200 flex items-center justify-between text-[11px]"
                >
                  <div className="flex items-center gap-2 text-slate-800">
                    <FileText className="w-3.5 h-3.5 text-blue-600" />
                    <span className="font-medium truncate max-w-[200px]">{d.title}</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-500">
                    <span className="font-mono text-blue-700 font-medium">{d.chunk_count} chunks</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold uppercase">
                      {d.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Live Vector Query Search Tester */}
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4">
          <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
            <Search className="w-4 h-4 text-emerald-600" />
            Vector Similarity Query Tester
          </h2>

          <form onSubmit={handleQuery} className="space-y-3 text-xs">
            <div>
              <label className="block text-slate-700 font-medium mb-1">Semantic Search Query</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  required
                  value={queryText}
                  onChange={(e) => setQueryText(e.target.value)}
                  placeholder="Enter semantic question..."
                  className="flex-1 bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs"
                />
                <button
                  type="submit"
                  disabled={searching || !selectedKBId}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold shadow-xs flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  <Search className="w-3.5 h-3.5" />
                  {searching ? "Searching..." : "Retrieve"}
                </button>
              </div>
            </div>
          </form>

          {/* Results List */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between text-xs text-slate-600 font-medium">
              <span>Top Retrieved Passages</span>
              <span className="font-mono text-[11px] text-blue-700 font-semibold">{queryResults.length} matches</span>
            </div>

            {queryResults.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs border border-dashed border-slate-200 rounded-lg">
                Enter a question above and click "Retrieve" to test cosine similarity vector retrieval against indexed documents.
              </div>
            ) : (
              <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
                {queryResults.map((r, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5 hover:border-slate-300 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-900">{r.title}</span>
                      <span className="text-xs font-mono font-bold text-emerald-700 px-2 py-0.5 rounded bg-emerald-50 border border-emerald-200">
                        Score: {(r.score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-500 font-mono truncate">
                      Source: {r.source}
                    </div>
                    <p className="text-xs text-slate-800 leading-relaxed bg-white p-3 rounded-md border border-slate-200 shadow-2xs">
                      {r.text}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
