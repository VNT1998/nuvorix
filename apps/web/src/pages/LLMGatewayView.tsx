import React, { useState, useRef } from "react";
import { Workload, CostSummary } from "../types";
import { api } from "../lib/api";
import { Coins, Send, PieChart, Square, Copy, Check } from "lucide-react";

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
  const [streamEnabled, setStreamEnabled] = useState(true);

  const [loading, setLoading] = useState(false);
  const [streamingResponse, setStreamingResponse] = useState("");
  const [chatResult, setChatResult] = useState<any>(null);
  const [copied, setCopied] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setLoading(false);
    }
  };

  const handleCopy = () => {
    const textToCopy = streamEnabled ? (streamingResponse || chatResult?.response) : chatResult?.response;
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSendPrompt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWorkloadId || !prompt.trim()) return;
    setLoading(true);
    setStreamingResponse("");
    setChatResult(null);

    if (streamEnabled) {
      const controller = new AbortController();
      abortControllerRef.current = controller;
      try {
        let textAccumulator = "";
        await api.streamGatewayChat(
          selectedWorkloadId,
          prompt,
          provider,
          model,
          (token) => {
            textAccumulator += token;
            setStreamingResponse(textAccumulator);
          },
          (meta) => {
            setChatResult({
              response: textAccumulator,
              provider,
              model,
              latency_ms: meta.latency_ms || 45,
              input_tokens: meta.input_tokens || Math.max(prompt.split(" ").length * 2, 1),
              output_tokens: meta.output_tokens || Math.max(textAccumulator.split(" ").length * 2, 1),
              estimated_cost: meta.cost || 0.0001,
            });
            onRefreshCosts();
          },
          controller.signal
        );
      } catch (err: any) {
        if (err.name !== "AbortError") {
          alert(`Gateway streaming failed: ${err.message}`);
        }
      } finally {
        setLoading(false);
        abortControllerRef.current = null;
      }
    } else {
      try {
        const res = await api.gatewayChat(selectedWorkloadId, prompt, provider, model);
        setChatResult(res);
        await onRefreshCosts();
      } catch (err: any) {
        alert(`Gateway call failed: ${err.message}`);
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <Coins className="w-5 h-5 text-amber-600" />
          LLM Gateway & FinOps Usage Metering
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Provider-agnostic routing, real-time SSE streaming, token accounting, per-request latency tracking, and organization cost allocation.
        </p>
      </div>

      {/* FinOps KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <div className="text-slate-500 text-xs font-medium">Total Organization Cost</div>
          <div className="mt-2 text-2xl font-bold text-slate-900 font-mono">
            ${costs ? costs.total_cost.toFixed(5) : "0.00000"}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Accumulated spend across all providers</div>
        </div>
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <div className="text-slate-500 text-xs font-medium">Total Requests</div>
          <div className="mt-2 text-2xl font-bold text-slate-900">{costs?.total_requests || 0}</div>
          <div className="text-[10px] text-slate-500 mt-1">Metered Gateway invocations</div>
        </div>
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <div className="text-slate-500 text-xs font-medium">Input Tokens</div>
          <div className="mt-2 text-2xl font-bold text-blue-700 font-mono">
            {(costs?.total_input_tokens || 0).toLocaleString()}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Prompt tokens processed</div>
        </div>
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <div className="text-slate-500 text-xs font-medium">Output Tokens</div>
          <div className="mt-2 text-2xl font-bold text-indigo-700 font-mono">
            {(costs?.total_output_tokens || 0).toLocaleString()}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Synthesized response tokens</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Gateway Request Simulator */}
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4">
          <h2 className="text-sm font-semibold text-slate-900">Gateway Request Simulator</h2>

          <form onSubmit={handleSendPrompt} className="space-y-4 text-xs">
            <div>
              <label className="block text-slate-700 font-medium mb-1">Workload Scope</label>
              <select
                value={selectedWorkloadId}
                onChange={(e) => setSelectedWorkloadId(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs cursor-pointer"
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
                <label className="block text-slate-700 font-medium mb-1">Provider Route</label>
                <select
                  value={provider}
                  onChange={(e) => {
                    const p = e.target.value;
                    setProvider(p);
                    if (p === "openai") setModel("gpt-4o-mini");
                    else if (p === "anthropic") setModel("claude-3-5-sonnet");
                    else if (p === "gemini") setModel("gemini-1.5-flash");
                    else setModel("llama-3-8b-instruct");
                  }}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs cursor-pointer"
                >
                  <option value="local">Local Deterministic</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="gemini">Google Gemini</option>
                  <option value="ollama">Ollama (Self-Hosted)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-700 font-medium mb-1">Model Target</label>
                <input
                  type="text"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 font-mono text-[11px] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs"
                />
              </div>
            </div>

            <div className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-50 border border-slate-200">
              <input
                type="checkbox"
                id="streamModeToggle"
                checked={streamEnabled}
                onChange={(e) => setStreamEnabled(e.target.checked)}
                className="rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer"
              />
              <label htmlFor="streamModeToggle" className="text-[11px] text-slate-700 cursor-pointer select-none">
                Enable Server-Sent Events (SSE) Streaming
              </label>
            </div>

            <div>
              <label className="block text-slate-700 font-medium mb-1">Prompt Payload</label>
              <textarea
                required
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={4}
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 font-mono text-[11px] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs"
              />
            </div>

            <div className="flex gap-2">
              <button
                type="submit"
                disabled={loading || !selectedWorkloadId}
                className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold shadow-xs flex items-center justify-center gap-2 cursor-pointer transition-all disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                {loading ? "Generating..." : "Send Request"}
              </button>
              {loading && (
                <button
                  type="button"
                  onClick={handleStopGeneration}
                  className="px-4 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg font-semibold shadow-xs flex items-center justify-center gap-1.5 cursor-pointer transition-all"
                >
                  <Square className="w-3 h-3 fill-current" />
                  Stop
                </button>
              )}
            </div>
          </form>
        </div>

        {/* Right Column: Gateway Response & Cost Breakdown */}
        <div className="lg:col-span-2 space-y-4">
          <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-900">Gateway Response & Telemetry</h2>
              <div className="flex items-center gap-3">
                {chatResult && (
                  <div className="flex items-center gap-3 font-mono text-xs text-slate-500">
                    <span className="text-blue-700 font-semibold">{chatResult.latency_ms}ms</span>
                    <span>•</span>
                    <span className="text-slate-800 font-semibold">{chatResult.input_tokens + chatResult.output_tokens} tokens</span>
                    <span>•</span>
                    <span className="text-amber-700 font-semibold">${chatResult.estimated_cost}</span>
                  </div>
                )}
                {(streamingResponse || chatResult?.response) && (
                  <button
                    onClick={handleCopy}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] rounded bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 cursor-pointer transition-all"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-600" />
                        <span className="text-emerald-700 font-medium">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {loading && streamingResponse ? (
              <div className="space-y-3">
                <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 font-mono text-xs text-slate-800 whitespace-pre-wrap leading-relaxed shadow-2xs animate-pulse">
                  {streamingResponse}
                  <span className="inline-block w-1.5 h-3.5 bg-blue-600 ml-1 translate-y-0.5 animate-bounce" />
                </div>
              </div>
            ) : chatResult ? (
              <div className="space-y-3">
                <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 font-mono text-xs text-slate-800 whitespace-pre-wrap leading-relaxed shadow-2xs">
                  {chatResult.response}
                </div>
                <div className="grid grid-cols-4 gap-2 text-center text-xs">
                  <div className="p-2.5 rounded bg-slate-50 border border-slate-200 shadow-2xs">
                    <div className="text-[10px] text-slate-500 font-medium">Provider</div>
                    <div className="font-semibold text-slate-900 uppercase mt-0.5">{chatResult.provider}</div>
                  </div>
                  <div className="p-2.5 rounded bg-slate-50 border border-slate-200 shadow-2xs">
                    <div className="text-[10px] text-slate-500 font-medium">Input Tokens</div>
                    <div className="font-mono font-semibold text-blue-700 mt-0.5">{chatResult.input_tokens}</div>
                  </div>
                  <div className="p-2.5 rounded bg-slate-50 border border-slate-200 shadow-2xs">
                    <div className="text-[10px] text-slate-500 font-medium">Output Tokens</div>
                    <div className="font-mono font-semibold text-indigo-700 mt-0.5">{chatResult.output_tokens}</div>
                  </div>
                  <div className="p-2.5 rounded bg-slate-50 border border-slate-200 shadow-2xs">
                    <div className="text-[10px] text-slate-500 font-medium">Estimated Cost</div>
                    <div className="font-mono font-semibold text-amber-700 mt-0.5">${chatResult.estimated_cost}</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-slate-500 text-xs border border-dashed border-slate-200 rounded-lg">
                Submit a prompt to inspect provider routing, token accounting, and cost calculations.
              </div>
            )}
          </div>

          {/* FinOps Allocation Tables */}
          {costs && (
            <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-3">
              <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-1.5">
                <PieChart className="w-4 h-4 text-slate-600" />
                Cost Attribution Breakdown
              </h3>
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <div className="text-slate-500 font-medium mb-1.5 text-[11px]">Spend by Model</div>
                  <div className="space-y-1">
                    {Object.entries(costs.breakdown_by_model).map(([m, c]) => (
                      <div key={m} className="flex justify-between items-center py-1 border-b border-slate-100 font-mono">
                        <span className="text-slate-700 truncate max-w-[140px]">{m}</span>
                        <span className="font-semibold text-slate-900">${c.toFixed(5)}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-slate-500 font-medium mb-1.5 text-[11px]">Spend by Provider</div>
                  <div className="space-y-1">
                    {Object.entries(costs.breakdown_by_provider).map(([p, c]) => (
                      <div key={p} className="flex justify-between items-center py-1 border-b border-slate-100 font-mono">
                        <span className="text-slate-700 uppercase">{p}</span>
                        <span className="font-semibold text-slate-900">${c.toFixed(5)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
