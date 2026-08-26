import React from "react";
import { AlertCircle, CheckCircle2, RefreshCw, Terminal } from "lucide-react";

export default function ExecutionLog({ logs, isProcessing }) {
  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-7 shadow-xl flex-1 flex flex-col font-mono text-sm">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
        <span className="font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Terminal className="w-5 h-5 text-emerald-400" /> Automated Execution
          Trace
        </span>
        <span className="text-xs text-emerald-400 bg-emerald-950/60 px-2.5 py-1 rounded-md border border-emerald-800/50">
          Autonomous Mode: ON
        </span>
      </div>
      <div className="space-y-3 overflow-y-auto flex-1 pr-2">
        {isProcessing && (
          <div className="flex items-center gap-3 py-2 text-emerald-300">
            <RefreshCw className="w-5 h-5 animate-spin" />
            Waiting for agent response...
          </div>
        )}
        {!isProcessing &&
          logs.map((log) => (
            <div
              key={log.id}
              className="flex items-start space-x-3 py-2 border-b border-slate-800/60 last:border-0"
            >
              <span className="text-slate-500 shrink-0 font-medium">
                [{log.time}]
              </span>
              {log.status === "error" ? (
                <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              ) : (
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              )}
              <span
                className={
                  log.status === "error"
                    ? "text-rose-300 text-sm leading-snug"
                    : "text-slate-200 text-sm leading-snug"
                }
              >
                {log.text}
              </span>
            </div>
          ))}
      </div>
    </div>
  );
}
