import React from "react";
import { MessageSquare, RefreshCw, Send } from "lucide-react";

export default function ChannelSimulator({
  clientName,
  inputMessage,
  isProcessing,
  presets,
  onClientNameChange,
  onMessageChange,
  onSimulate,
}) {
  return (
    <div className="lg:col-span-5 flex flex-col justify-between bg-slate-900/60 border border-slate-800 rounded-2xl p-7 shadow-xl">
      <div className="space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <span className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-emerald-400" /> Inbound
            Client Channel
          </span>
          <span className="text-xs font-mono text-slate-400 bg-slate-800/80 px-2 py-1 rounded">
            Channel: Web / SMS
          </span>
        </div>
        <div>
          <label className="text-sm text-slate-300 block mb-2 font-medium">
            Quick Presets:
          </label>
          <div className="flex flex-col gap-2.5">
            {presets.map((message, index) => (
              <button
                key={index}
                onClick={() => onMessageChange(message)}
                className="text-left text-sm bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 p-3 rounded-xl text-slate-200 transition-colors"
              >
                &quot;{message}&quot;
              </button>
            ))}
          </div>
        </div>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-slate-300 block mb-1.5">
              Client Name
            </label>
            <input
              type="text"
              value={clientName}
              onChange={(event) => onClientNameChange(event.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-base text-slate-100 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-300 block mb-1.5">
              Unstructured Issue Description
            </label>
            <textarea
              rows={4}
              value={inputMessage}
              onChange={(event) => onMessageChange(event.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl p-4 text-base text-slate-100 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
              placeholder="Describe the issue..."
            />
          </div>
        </div>
      </div>
      <button
        onClick={onSimulate}
        disabled={isProcessing}
        className="w-full mt-6 py-3.5 px-5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white font-semibold rounded-xl transition flex items-center justify-center gap-2.5 text-base shadow-lg shadow-emerald-950/50"
      >
        {isProcessing ? (
          <RefreshCw className="w-5 h-5 animate-spin" />
        ) : (
          <Send className="w-5 h-5" />
        )}
        {isProcessing ? "Agent Orchestrating..." : "Simulate Incoming Request"}
      </button>
    </div>
  );
}
