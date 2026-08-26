import React from "react";
import { AlertTriangle, Clock, Server } from "lucide-react";

export default function TicketSummary({ analysis }) {
  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-7 shadow-xl">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-5">
        <span className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Server className="w-5 h-5 text-emerald-400" /> AI Extraction &amp;
          Context Analysis
        </span>
        <div className="flex items-center gap-2 text-sm font-mono text-slate-400">
          <Clock className="w-4 h-4" />
          <span>{analysis.timestamp}</span>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
        <SummaryField label="Category" value={analysis.category} />
        <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
            Urgency Rating
          </span>
          <span
            className={`text-base font-bold mt-1 inline-flex items-center gap-2 ${analysis.urgency.includes("Critical") ? "text-rose-400" : "text-amber-400"}`}
          >
            <AlertTriangle className="w-4 h-4" />
            {analysis.urgency}
          </span>
        </div>
        <SummaryField label="Detected Device" value={analysis.deviceType} />
      </div>
      <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl text-sm text-slate-200 leading-relaxed">
        <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold block mb-1">
          Triaged Issue Summary:
        </span>
        &quot;{analysis.summary}&quot;
      </div>
    </div>
  );
}

function SummaryField({ label, value }) {
  return (
    <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
        {label}
      </span>
      <span className="text-base font-bold text-slate-100 mt-1 block">
        {value}
      </span>
    </div>
  );
}
