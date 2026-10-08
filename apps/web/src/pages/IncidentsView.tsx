import React, { useState } from "react";
import { Incident } from "../types";
import { api } from "../lib/api";
import { AlertTriangle, CheckCircle2, RotateCcw, ShieldAlert, Sparkles, Activity } from "lucide-react";

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
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-rose-400" />
          Incident Detection & AI Root Cause Analysis (RCA)
        </h1>
        <p className="text-xs text-slate-400 mt-1">
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
                  ? "bg-slate-900/90 border-rose-500/40 shadow-lg shadow-rose-950/20"
                  : "bg-slate-900/40 border-slate-800/80"
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
                      <h2 className="text-sm font-bold text-slate-100">{inc.title}</h2>
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      Detected: {new Date(inc.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                      inc.severity === "HIGH" || inc.severity === "CRITICAL"
                        ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                        : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                    }`}
                  >
                    {inc.severity} Severity
                  </span>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase border ${
                      isOpen
                        ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
                        : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                    }`}
                  >
                    {inc.status}
                  </span>
                </div>
              </div>

              {/* RCA Finding Box */}
              <div className="mt-4 p-4 rounded-xl bg-slate-950 border border-slate-850 space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-indigo-400 flex items-center gap-1.5 uppercase tracking-wider">
                    <Sparkles className="w-3.5 h-3.5" />
                    AI Root Cause Analysis Hypothesis
                  </span>
                  <span className="font-mono text-[11px] text-cyan-400 font-bold">
                    Confidence: {(inc.confidence * 100).toFixed(0)}%
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed font-sans">{inc.root_cause}</p>

                {/* Evidence list */}
                {inc.evidence && inc.evidence.length > 0 && (
                  <div className="pt-2 border-t border-slate-900 space-y-1">
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                      Correlated Signals & Evidence:
                    </span>
                    <ul className="text-xs text-slate-400 list-disc list-inside space-y-1">
                      {inc.evidence.map((ev, i) => (
                        <li key={i}>{ev}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Recommendation & Remediation Button */}
              <div className="mt-4 pt-3 border-t border-slate-850 flex items-center justify-between">
                <div className="text-xs text-slate-300">
                  <span className="text-slate-500 font-medium">Recommendation: </span>
                  <span className="font-semibold text-emerald-400">{inc.recommendation}</span>
                </div>

                {isOpen && (
                  <button
                    onClick={() => handleRemediate(inc.id)}
                    disabled={remediating === inc.id}
                    className="px-4 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-rose-600/30 flex items-center gap-1.5 cursor-pointer transition-all disabled:opacity-50"
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
