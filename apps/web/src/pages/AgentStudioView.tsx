import React, { useState, useEffect } from "react";
import { Workload, KnowledgeBase, AgentRunResponse, ToolDeclaration } from "../types";
import { api } from "../lib/api";
import { Bot, Send, ShieldAlert, Cpu, CheckCircle2, ArrowRight, Clock, Sparkles } from "lucide-react";

interface AgentStudioViewProps {
  workloads: Workload[];
  knowledgeBases: KnowledgeBase[];
}

export const AgentStudioView: React.FC<AgentStudioViewProps> = ({
  workloads,
  knowledgeBases,
}) => {
  const agentWorkloads = workloads.filter((w) => w.type === "agent" || w.type === "rag");
  const [selectedWorkloadId, setSelectedWorkloadId] = useState(agentWorkloads[0]?.id || "");
  const [selectedKBId, setSelectedKBId] = useState(knowledgeBases[0]?.id || "");
  const [prompt, setPrompt] = useState("Search knowledge base for platform architecture and check deployment status");
  const [allowHighRisk, setAllowHighRisk] = useState(false);

  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<AgentRunResponse | null>(null);
  const [tools, setTools] = useState<ToolDeclaration[]>([]);

  useEffect(() => {
    loadTools();
  }, []);

  const loadTools = async () => {
    try {
      const t = await api.getTools();
      setTools(t);
    } catch (_) {}
  };

  const handleRunAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWorkloadId || !prompt.trim()) return;
    setRunning(true);
    try {
      const res = await api.runAgent(selectedWorkloadId, prompt, selectedKBId, allowHighRisk);
      setResult(res);
    } catch (err: any) {
      alert(`Agent execution failed: ${err.message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <Bot className="w-5 h-5 text-purple-400" />
          Agent Runtime & MCP Tool Execution Studio
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Stateful LangGraph orchestration with multi-step planning, tool observation loops, and MCP permission authorization boundaries.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Prompt & Execution Controls */}
        <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4">
          <h2 className="text-sm font-semibold text-slate-200">Execution Configuration</h2>

          <form onSubmit={handleRunAgent} className="space-y-4 text-xs">
            <div>
              <label className="block text-slate-400 mb-1">Target Agent Workload</label>
              <select
                value={selectedWorkloadId}
                onChange={(e) => setSelectedWorkloadId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 cursor-pointer"
              >
                {agentWorkloads.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} ({w.active_version || "none"})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Attached Knowledge Base (RAG)</label>
              <select
                value={selectedKBId}
                onChange={(e) => setSelectedKBId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 cursor-pointer"
              >
                {knowledgeBases.map((kb) => (
                  <option key={kb.id} value={kb.id}>
                    {kb.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Operator Prompt</label>
              <textarea
                required
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={4}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 font-mono text-[11px]"
              />
            </div>

            <div className="flex items-center gap-2 p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <input
                type="checkbox"
                id="highRiskToggle"
                checked={allowHighRisk}
                onChange={(e) => setAllowHighRisk(e.target.checked)}
                className="rounded border-slate-700 text-indigo-600 focus:ring-0 cursor-pointer"
              />
              <label htmlFor="highRiskToggle" className="text-[11px] text-slate-300 cursor-pointer select-none">
                Authorize High-Risk MCP Tools (e.g. emergency circuit breaker)
              </label>
            </div>

            <button
              type="submit"
              disabled={running || !selectedWorkloadId}
              className="w-full py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg font-semibold shadow-md shadow-purple-600/20 flex items-center justify-center gap-2 cursor-pointer transition-all disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              {running ? "Executing LangGraph Graph..." : "Execute Agent Workflow"}
            </button>
          </form>

          {/* MCP Tools Registry List */}
          <div className="pt-3 border-t border-slate-800 space-y-2">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Available MCP Tools & Guardrails
            </span>
            <div className="space-y-1.5">
              {tools.map((t) => (
                <div
                  key={t.name}
                  className="p-2.5 rounded bg-slate-950/60 border border-slate-800/80 text-[11px] space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-slate-200">{t.name}</span>
                    <span
                      className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase ${
                        t.risk === "high"
                          ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                          : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                      }`}
                    >
                      {t.risk} risk
                    </span>
                  </div>
                  <p className="text-slate-400 text-[10px]">{t.description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Execution Traces and Synthesized Answer */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-400" />
              LangGraph Step-by-Step Execution Trace
            </h2>
            {result && (
              <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
                <span className="text-indigo-400">{result.duration_ms}ms</span>
                <span>•</span>
                <span className="text-amber-400">${result.estimated_cost}</span>
              </div>
            )}
          </div>

          {result ? (
            <div className="space-y-4">
              {/* Steps timeline */}
              <div className="space-y-3">
                {result.steps.map((step) => (
                  <div
                    key={step.step}
                    className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-2"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="w-5 h-5 rounded-full bg-slate-800 flex items-center justify-center font-bold text-[10px] text-slate-300">
                          {step.step}
                        </span>
                        <span className="font-bold uppercase tracking-wider text-indigo-400">
                          {step.stage.replace("_", " ")}
                        </span>
                        {step.tool_name && (
                          <span className="font-mono text-cyan-400 px-1.5 py-0.5 rounded bg-cyan-950/40 border border-cyan-800/30 text-[10px]">
                            {step.tool_name}
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] font-mono text-slate-500">{step.latency_ms}ms</span>
                    </div>

                    <p className="text-xs text-slate-300 whitespace-pre-wrap">{step.content}</p>

                    {/* Tool output excerpt */}
                    {step.tool_output && (
                      <div className="mt-2 p-2.5 rounded bg-slate-900 border border-slate-800 font-mono text-[10px] text-slate-400 overflow-x-auto max-h-36">
                        {JSON.stringify(step.tool_output, null, 2)}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Synthesized Response */}
              <div className="p-4 rounded-xl bg-purple-950/20 border border-purple-800/40 space-y-2">
                <span className="text-xs font-bold text-purple-300 uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  Synthesized Agent Response
                </span>
                <p className="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap">
                  {result.final_response}
                </p>
              </div>
            </div>
          ) : (
            <div className="p-16 text-center text-slate-500 text-xs border border-dashed border-slate-800 rounded-lg">
              No agent loop executed yet. Submit a prompt on the left to observe the step-by-step LangGraph planner, tool selection, observation, and synthesized answer.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
