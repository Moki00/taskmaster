import React from "react";
import {
  Tag,
  AlertTriangle,
  Laptop,
  FileText,
  MessageSquareQuote,
  CheckCircle2,
} from "lucide-react";

export default function TicketSummary({ analysis }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2 text-slate-400">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <h2 className="text-sm font-semibold tracking-wide uppercase">
            Ticket &amp; SLA Analysis
          </h2>
        </div>
        {analysis.ticketNumber && (
          <span className="text-xs font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2.5 py-1 rounded-md">
            #{analysis.ticketNumber}
          </span>
        )}
      </div>

      {/* 3 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Category Card */}
        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800/80">
          <div className="flex items-center space-x-1.5 text-slate-400 mb-1">
            <Tag className="w-3.5 h-3.5" />
            <span className="text-xs">CATEGORY</span>
          </div>
          <span className="text-sm font-semibold text-white">
            {analysis.category || "General"}
          </span>
        </div>

        {/* Urgency Rating Card */}
        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800/80">
          <div className="flex items-center space-x-1.5 text-slate-400 mb-1">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-xs">URGENCY RATING</span>
          </div>
          <span className="text-sm font-semibold text-amber-400">
            {analysis.urgency || "Normal"}
          </span>
        </div>

        {/* Detected Device Card */}
        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800/80">
          <div className="flex items-center space-x-1.5 text-slate-400 mb-1">
            <Laptop className="w-3.5 h-3.5" />
            <span className="text-xs">DETECTED DEVICE</span>
          </div>
          <span className="text-sm font-semibold text-white">
            {analysis.deviceType || "Workstation"}
          </span>
        </div>
      </div>

      {/* Triaged Issue Summary */}
      <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800/80">
        <div className="flex items-center space-x-1.5 text-slate-400 mb-1">
          <FileText className="w-3.5 h-3.5" />
          <span className="text-xs">TRIAGED ISSUE SUMMARY</span>
        </div>
        <p className="text-sm text-slate-300 italic">
          "{analysis.summary || "No description provided."}"
        </p>
      </div>

      {/* Customer Reply Draft Box */}
      {analysis.draftReply && (
        <div className="bg-emerald-950/20 border border-emerald-500/30 rounded-xl p-4 mt-2">
          <div className="flex items-center space-x-2 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <MessageSquareQuote className="w-4 h-4" />
            <span>Autonomous Customer Reply Draft</span>
          </div>
          <p className="text-sm text-slate-200 font-mono bg-slate-950/70 p-3 rounded-lg border border-emerald-500/20 leading-relaxed">
            {analysis.draftReply}
          </p>
        </div>
      )}
    </div>
  );
}
