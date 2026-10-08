import React, { useState, useEffect } from "react";
import { AuditEvent } from "../types";
import { api } from "../lib/api";
import { History, Shield, RefreshCw } from "lucide-react";

export const AuditTrailView: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadEvents();
  }, []);

  const loadEvents = async () => {
    setLoading(true);
    try {
      const data = await api.getAuditEvents();
      setEvents(data);
    } catch (_) {
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <History className="w-5 h-5 text-indigo-400" />
            Security & Operational Audit Trail
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Immutable log of all platform operations, release promotions, rollbacks, and authorization decisions.
          </p>
        </div>
        <button
          onClick={loadEvents}
          disabled={loading}
          className="px-3 py-1.5 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 rounded-lg text-xs font-medium flex items-center gap-1.5 cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh Log
        </button>
      </div>

      <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px] tracking-wider">
                <th className="pb-3 font-semibold">Timestamp</th>
                <th className="pb-3 font-semibold">Action</th>
                <th className="pb-3 font-semibold">Actor / User</th>
                <th className="pb-3 font-semibold">Resource Type</th>
                <th className="pb-3 font-semibold">Resource ID</th>
                <th className="pb-3 font-semibold">Metadata</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {events.map((e) => (
                <tr key={e.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-2.5 font-mono text-[11px] text-slate-400">
                    {new Date(e.created_at).toLocaleTimeString()}
                  </td>
                  <td className="py-2.5">
                    <span className="font-mono text-[11px] font-semibold text-indigo-300 px-2 py-0.5 rounded bg-indigo-950/40 border border-indigo-800/30">
                      {e.action}
                    </span>
                  </td>
                  <td className="py-2.5 font-mono text-[11px] text-slate-300">{e.user_id}</td>
                  <td className="py-2.5 text-[11px] text-slate-400 capitalize">{e.resource_type}</td>
                  <td className="py-2.5 font-mono text-[11px] text-slate-500 truncate max-w-[120px]">
                    {e.resource_id || "system"}
                  </td>
                  <td className="py-2.5 font-mono text-[10px] text-slate-400 truncate max-w-[200px]">
                    {JSON.stringify(e.metadata)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
