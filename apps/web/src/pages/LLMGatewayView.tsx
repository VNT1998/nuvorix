import React, { useState } from "react";
import { Workload, CostSummary } from "../types";
import { api } from "../lib/api";
import { Coins, Send, Cpu, DollarSign, Activity, PieChart } from "lucide-react";

interface LLMGatewayViewProps {
  workloads: Workload[];
  costs: CostSummary | null;
  onRefreshCosts: () => Promise<void>;
}

export const LLMGatewayView: React.FC<LLMGatewayViewProps> = ({
  workloads,
  costs,
  onRefreshCosts,
}) => {
  const [selectedWorkloadId, setSelectedWorkloadId] = useState(workloads[0]?.id || "");
  const [prompt, setPrompt] = useState("Explain how Nuvorix enforces release policy gates before deployment.");
  const [provider, setProvider] = useState("local");
  const [model, setModel] = useState("llama-3-8b-instruct");

  const [loading, setLoading] = useState(false);
  const [chatResult, setChatResult] = useState<any>(null);

  const handleSendPrompt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWorkloadId || !prompt.trim()) return;
    setLoading(true);
    try {
      const res = await api.gatewayChat(selectedWorkloadId, prompt, provider, model);
      setChatResult(res);
      await onRefreshCosts();
    } catch (err: any) {
      alert(`Gateway call failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <Coins className="w-5 h-5 text-amber-400" />
          LLM Gateway & FinOps Usage Metering
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Provider-agnostic routing, token accounting, per-request latency tracking, and organization cost allocation.
        </p>
      </div>

      {/* FinOps KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
          <div className="text-slate-400 text-xs">Total Organization Cost</div>
          <div className="mt-2 text-2xl font-bold text-amber-400 font-mono">
            ${costs ? costs.total_cost.toFixed(5) : "0.00000"}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Accumulated spend across all providers</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
          <div className="text-slate-400 text-xs">Total Requests</div>
          <div className="mt-2 text-2xl font-bold text-slate-100">{costs?.total_requests || 0}</div>
          <div className="text-[10px] text-slate-500 mt-1">Metered Gateway invocations</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
          <div className="text-slate-400 text-xs">Input Tokens</div>
          <div className="mt-2 text-2xl font-bold text-cyan-400 font-mono">
            {(costs?.total_input_tokens || 0).toLocaleString()}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Prompt tokens processed</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
          <div className="text-slate-400 text-xs">Output Tokens</div>
          <div className="mt-2 text-2xl font-bold text-indigo-400 font-mono">
            {(costs?.total_output_tokens || 0).toLocaleString()}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Synthesized response tokens</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Gateway Playground */}
        <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4">
          <h2 className="text-sm font-semibold text-slate-200">Gateway Request Simulator</h2>

          <form onSubmit={handleSendPrompt} className="space-y-4 text-xs">
            <div>
              <label className="block text-slate-400 mb-1">Workload Scope</label>
              <select
                value={selectedWorkloadId}
                onChange={(e) => setSelectedWorkloadId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 cursor-pointer"
              >
                {workloads.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} ({w.type})
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-400 mb-1">Provider</label>
                <select
                  value={provider}
                  onChange={(e) => {
                    const p = e.target.value;
                    setProvider(p);
                    if (p === "openai") setModel("gpt-4o");
                    else if (p === "anthropic") setModel("claude-3-5-sonnet");
                    else if (p === "gemini") setModel("gemini-1.5-pro");
                    else setModel("llama-3-8b-instruct");
                  }}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 cursor-pointer"
                >
                  <option value="local">Local Model</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="gemini">Google Gemini</option>
                </select>
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Model</label>
                <input
                  type="text"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-2 text-slate-200 font-mono text-[11px]"
                />
              </div>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Query Prompt</label>
              <textarea
                required
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={4}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 font-mono text-[11px] focus:outline-none focus:border-indigo-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !selectedWorkloadId}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-semibold shadow-md shadow-indigo-600/20 flex items-center justify-center gap-2 cursor-pointer transition-all disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              {loading ? "Routing via Gateway..." : "Send Request"}
            </button>
          </form>
        </div>

        {/* Right Column: Gateway Response & Cost Breakdown */}
        <div className="lg:col-span-2 space-y-4">
          {/* Response Box */}
          <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-200">Gateway Response & Telemetry</h2>
              {chatResult && (
                <div className="flex items-center gap-3 font-mono text-xs text-slate-400">
                  <span className="text-indigo-400">{chatResult.latency_ms}ms</span>
                  <span>•</span>
                  <span className="text-cyan-400">{chatResult.input_tokens + chatResult.output_tokens} tokens</span>
                  <span>•</span>
                  <span className="text-amber-400">${chatResult.estimated_cost}</span>
                </div>
              )}
            </div>

            {chatResult ? (
              <div className="space-y-3">
                <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
                  {chatResult.response}
                </div>
                <div className="grid grid-cols-4 gap-2 text-center text-xs">
                  <div className="p-2 rounded bg-slate-950 border border-slate-850">
                    <div className="text-[10px] text-slate-500">Provider</div>
                    <div className="font-semibold text-slate-300 uppercase mt-0.5">{chatResult.provider}</div>
                  </div>
                  <div className="p-2 rounded bg-slate-950 border border-slate-850">
                    <div className="text-[10px] text-slate-500">Input Tokens</div>
                    <div className="font-mono font-semibold text-cyan-400 mt-0.5">{chatResult.input_tokens}</div>
                  </div>
                  <div className="p-2 rounded bg-slate-950 border border-slate-850">
                    <div className="text-[10px] text-slate-500">Output Tokens</div>
                    <div className="font-mono font-semibold text-indigo-400 mt-0.5">{chatResult.output_tokens}</div>
                  </div>
                  <div className="p-2 rounded bg-slate-950 border border-slate-850">
                    <div className="text-[10px] text-slate-500">Estimated Cost</div>
                    <div className="font-mono font-semibold text-amber-400 mt-0.5">${chatResult.estimated_cost}</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-slate-500 text-xs border border-dashed border-slate-800 rounded-lg">
                Submit a request on the left to route through the LLM Gateway and observe latency, token counts, and cost breakdown.
              </div>
            )}
          </div>

          {/* Breakdown by Model */}
          {costs && Object.keys(costs.breakdown_by_model).length > 0 && (
            <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800">
              <h2 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
                <PieChart className="w-4 h-4 text-indigo-400" />
                Cost Breakdown by Model & Provider
              </h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <span className="text-[11px] text-slate-400 uppercase font-semibold">By Model</span>
                  {Object.entries(costs.breakdown_by_model).map(([m, c]) => (
                    <div key={m} className="p-2.5 rounded bg-slate-950 border border-slate-850 flex justify-between text-xs">
                      <span className="font-mono text-slate-300">{m}</span>
                      <span className="font-mono font-bold text-amber-400">${c.toFixed(5)}</span>
                    </div>
                  ))}
                </div>
                <div className="space-y-2">
                  <span className="text-[11px] text-slate-400 uppercase font-semibold">By Provider</span>
                  {Object.entries(costs.breakdown_by_provider).map(([p, c]) => (
                    <div key={p} className="p-2.5 rounded bg-slate-950 border border-slate-850 flex justify-between text-xs">
                      <span className="font-medium text-slate-300 capitalize">{p}</span>
                      <span className="font-mono font-bold text-amber-400">${c.toFixed(5)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
