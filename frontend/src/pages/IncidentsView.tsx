import React, { useState } from "react";
import { Incident } from "../types";
import { api } from "../lib/api";
import { AlertTriangle, RotateCcw, Sparkles } from "lucide-react";

interface IncidentsViewProps {
  incidents: Incident[];
  onRefreshIncidents: () => Promise<void>;
  onRefreshDeployments: () => Promise<void>;
  onRefreshWorkloads: () => Promise<void>;
}

export const IncidentsView: React.FC<IncidentsViewProps> = ({
  incidents,
  onRefreshIncidents,
  onRefreshDeployments,
  onRefreshWorkloads,
}) => {
  const [remediating, setRemediating] = useState<string | null>(null);

  const handleRemediate = async (incidentId: string) => {
    if (!confirm("Execute automated remediation? This will trigger an immediate rollback to the preceding stable version.")) return;
    setRemediating(incidentId);
    try {
      const res = await api.remediateIncident(incidentId, "rollback");
      alert(`Remediation executed successfully! Status: ${res.status}`);
      await onRefreshIncidents();
      await onRefreshDeployments();
      await onRefreshWorkloads();
    } catch (err: any) {
      alert(`Remediation failed: ${err.message}`);
    } finally {
      setRemediating(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-rose-600" />
          Incident Detection & AI Root Cause Analysis (RCA)
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Automated anomaly detection across latency, errors, and vector search. The RCA agent correlates signals with rollout events and formulates remediation actions.
        </p>
      </div>

      <div className="space-y-4">
        {incidents.map((inc) => {
          const isOpen = inc.status !== "resolved";
          return (
            <div
              key={inc.id}
              className={`p-5 rounded-xl border transition-all ${
                isOpen
                  ? "bg-white border-rose-300 shadow-xs ring-1 ring-rose-200/60"
                  : "bg-white border-slate-200 shadow-xs"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div
                    className={`mt-1 w-3 h-3 rounded-full ${
                      isOpen ? "bg-rose-500 animate-pulse" : "bg-emerald-500"
                    }`}
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-slate-400">[{inc.id}]</span>
                      <h2 className="text-sm font-bold text-slate-900">{inc.title}</h2>
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      Detected: {new Date(inc.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase border ${
                      inc.severity === "HIGH" || inc.severity === "CRITICAL"
                        ? "bg-rose-50 text-rose-700 border-rose-200"
                        : "bg-amber-50 text-amber-700 border-amber-200"
                    }`}
                  >
                    {inc.severity} Severity
                  </span>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase border ${
                      isOpen
                        ? "bg-amber-50 text-amber-700 border-amber-200"
                        : "bg-emerald-50 text-emerald-700 border-emerald-200"
                    }`}
                  >
                    {inc.status}
                  </span>
                </div>
              </div>

              {/* RCA Finding Box */}
              <div className="mt-4 p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-blue-700 flex items-center gap-1.5 uppercase tracking-wider">
                    <Sparkles className="w-3.5 h-3.5" />
                    AI Root Cause Analysis Hypothesis
                  </span>
                  <span className="font-mono text-[11px] text-blue-700 font-bold px-2 py-0.5 rounded bg-blue-50 border border-blue-200">
                    Confidence: {(inc.confidence * 100).toFixed(0)}%
                  </span>
                </div>

                <p className="text-xs text-slate-800 leading-relaxed font-sans">{inc.root_cause}</p>

                {/* Evidence list */}
                {inc.evidence && inc.evidence.length > 0 && (
                  <div className="pt-2 border-t border-slate-200 space-y-1">
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                      Correlated Signals & Evidence:
                    </span>
                    <ul className="text-xs text-slate-600 list-disc list-inside space-y-1">
                      {inc.evidence.map((ev, i) => (
                        <li key={i}>{ev}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Recommendation & Remediation Button */}
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                <div className="text-xs text-slate-600">
                  <span className="text-slate-500 font-medium">Recommendation: </span>
                  <span className="font-semibold text-emerald-700">{inc.recommendation}</span>
                </div>

                {isOpen && (
                  <button
                    onClick={() => handleRemediate(inc.id)}
                    disabled={remediating === inc.id}
                    className="px-4 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow-xs flex items-center gap-1.5 cursor-pointer transition-all disabled:opacity-50"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    {remediating === inc.id ? "Remediating..." : "Remediate Incident (Rollback)"}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
