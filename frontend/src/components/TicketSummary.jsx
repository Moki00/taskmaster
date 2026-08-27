import React from "react";
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Tag,
  User,
  Wrench,
  MessageSquareQuote,
} from "lucide-react";

export default function TicketSummary({ analysis }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <h2 className="text-sm font-semibold tracking-wide uppercase text-slate-400">
          Ticket &amp; SLA Analysis
        </h2>
        {analysis.ticketNumber && (
          <span className="text-xs font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2.5 py-1 rounded-md">
            #{analysis.ticketNumber}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800/80">
          <span className="text-xs text-slate-400 block mb-1">CATEGORY</span>
          <span className="text-sm font-semibold text-white">
            {analysis.category}
          </span>
        </div>
        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800/80">
          <span className="text-xs text-slate-400 block mb-1">
            URGENCY RATING
          </span>
          <span className="text-sm font-semibold text-amber-400">
            {analysis.urgency}
          </span>
        </div>
        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800/80">
          <span className="text-xs text-slate-400 block mb-1">
            DETECTED DEVICE
          </span>
          <span className="text-sm font-semibold text-white">
            {analysis.deviceType}
          </span>
        </div>
      </div>

      <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800/80">
        <span className="text-xs text-slate-400 block mb-1">
          TRIAGED ISSUE SUMMARY
        </span>
        <p className="text-sm text-slate-300 italic">"{analysis.summary}"</p>
      </div>

      {analysis.draftReply && (
        <div className="bg-emerald-950/20 border border-emerald-500/30 rounded-xl p-4 mt-2">
          <div className="flex items-center space-x-2 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <MessageSquareQuote className="w-4 h-4" />
            <span>Autonomous Customer Reply Draft</span>
          </div>
          <p className="text-sm text-slate-200 font-mono bg-slate-950/70 p-3 rounded-lg border border-emerald-500/20">
            {analysis.draftReply}
          </p>
        </div>
      )}
    </div>
  );
}
