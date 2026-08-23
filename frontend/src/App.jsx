import React, { useState } from "react";
import {
  Terminal,
  Send,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Server,
  MessageSquare,
  RefreshCw,
  Cpu,
} from "lucide-react";

const PRESET_MESSAGES = [
  "Our main switch is down and the office network is completely dead! We have clients arriving in 20 minutes!",
  "My laptop screen is flickering blue and won't boot into Windows after the update.",
  "Looking to get a quote on setting up a new mesh Wi-Fi network for our small warehouse.",
];

export default function TaskmasterVisualizer() {
  const [inputMessage, setInputMessage] = useState(PRESET_MESSAGES[0]);
  const [clientName, setClientName] = useState("Alice Smith");
  const [isProcessing, setIsProcessing] = useState(false);

  const [analysis, setAnalysis] = useState({
    timestamp: "2026-08-22 15:04:12 UTC",
    client: "Alice Smith",
    category: "Network / Infrastructure",
    urgency: "Critical / High",
    deviceType: "Enterprise Switch / Gateway",
    summary: "Complete local area network failure affecting office operations.",
  });

  const [logs, setLogs] = useState([
    {
      id: 1,
      time: "15:04:13",
      text: "Ingestion verified from Client Webhook.",
      status: "ok",
    },
    {
      id: 2,
      time: "15:04:14",
      text: "Extracted parameters: Urgency=Critical, Target=Switch.",
      status: "ok",
    },
    {
      id: 3,
      time: "15:04:16",
      text: "Created Priority CRM Support Ticket #1042.",
      status: "ok",
    },
    {
      id: 4,
      time: "15:04:18",
      text: "Calendar Dispatch: Reserved Emergency Support window.",
      status: "ok",
    },
    {
      id: 5,
      time: "15:04:20",
      text: "Client Notified (SMS): Sent power-cycle checklist.",
      status: "ok",
    },
    {
      id: 6,
      time: "15:04:22",
      text: "Status transitioned to: Dispatched (Awaiting Tech).",
      status: "active",
    },
  ]);

  const handleSimulate = () => {
    setIsProcessing(true);
    setLogs([]);

    setTimeout(() => {
      const now =
        new Date().toISOString().replace("T", " ").substring(0, 19) + " UTC";
      setAnalysis({
        timestamp: now,
        client: clientName,
        category:
          inputMessage.toLowerCase().includes("switch") ||
          inputMessage.toLowerCase().includes("network")
            ? "Network / Infrastructure"
            : "Workstation / OS Support",
        urgency:
          inputMessage.toLowerCase().includes("dead") ||
          inputMessage.toLowerCase().includes("minutes")
            ? "Critical / High"
            : "Standard Priority",
        deviceType: inputMessage.toLowerCase().includes("switch")
          ? "Managed Switch"
          : "Client PC / Laptop",
        summary: inputMessage,
      });

      setLogs([
        {
          id: 1,
          time: "15:05:01",
          text: `Ingested payload from ${clientName}.`,
          status: "ok",
        },
        {
          id: 2,
          time: "15:05:02",
          text: "Gemini 3.5 Flash: JSON Schema validation passed.",
          status: "ok",
        },
        {
          id: 3,
          time: "15:05:03",
          text: "Ticket #1043 appended to dispatch queue.",
          status: "ok",
        },
        {
          id: 4,
          time: "15:05:04",
          text: "Autonomous calendar lock verified with Google Workspace.",
          status: "ok",
        },
        {
          id: 5,
          time: "15:05:05",
          text: "Auto-acknowledgment sent via Twilio / SendGrid.",
          status: "ok",
        },
      ]);
      setIsProcessing(false);
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-6 md:p-10 flex flex-col justify-between">
      {/* Top Header */}
      <header className="flex items-center justify-between pb-6 border-b border-slate-800 mb-8">
        <div className="flex items-center space-x-4">
          <div className="w-14 h-14 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Cpu className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-bold tracking-tight text-white">
                TASKMASTER
              </h1>
              <span className="text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2.5 py-1 rounded-full">
                AGENT ACTIVE
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-0.5">
              Autonomous IT Client Dispatch & Triage Coordinator
            </p>
          </div>
        </div>
        <div className="text-sm text-slate-400 font-mono flex items-center space-x-2 bg-slate-900 px-4 py-2 rounded-lg border border-slate-800">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>Google GenAI SDK · Gemini 3.5 Flash</span>
        </div>
      </header>

      {/* Main Split Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 flex-1">
        {/* Left Side: Client Simulator */}
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

            {/* Presets */}
            <div>
              <label className="text-sm text-slate-300 block mb-2 font-medium">
                Quick Presets:
              </label>
              <div className="flex flex-col gap-2.5">
                {PRESET_MESSAGES.map((msg, idx) => (
                  <button
                    key={idx}
                    onClick={() => setInputMessage(msg)}
                    className="text-left text-sm bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 p-3 rounded-xl text-slate-200 transition-colors"
                  >
                    "{msg}"
                  </button>
                ))}
              </div>
            </div>

            {/* Inputs */}
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-slate-300 block mb-1.5">
                  Client Name
                </label>
                <input
                  type="text"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
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
                  onChange={(e) => setInputMessage(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl p-4 text-base text-slate-100 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                  placeholder="Describe the issue..."
                />
              </div>
            </div>
          </div>

          <button
            onClick={handleSimulate}
            disabled={isProcessing}
            className="w-full mt-6 py-3.5 px-5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white font-semibold rounded-xl transition flex items-center justify-center gap-2.5 text-base shadow-lg shadow-emerald-950/50"
          >
            {isProcessing ? (
              <RefreshCw className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
            {isProcessing
              ? "Agent Orchestrating..."
              : "Simulate Incoming Request"}
          </button>
        </div>

        {/* Right Side: Taskmaster Mission Control */}
        <div className="lg:col-span-7 flex flex-col space-y-6">
          {/* AI Structured Extraction Box */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-7 shadow-xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-5">
              <span className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <Server className="w-5 h-5 text-emerald-400" /> AI Extraction &
                Context Analysis
              </span>
              <div className="flex items-center gap-2 text-sm font-mono text-slate-400">
                <Clock className="w-4 h-4" />
                <span>{analysis.timestamp}</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
              <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                  Category
                </span>
                <span className="text-base font-bold text-slate-100 mt-1 block">
                  {analysis.category}
                </span>
              </div>
              <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                  Urgency Rating
                </span>
                <span
                  className={`text-base font-bold mt-1 inline-flex items-center gap-2 ${
                    analysis.urgency.includes("Critical")
                      ? "text-rose-400"
                      : "text-amber-400"
                  }`}
                >
                  <AlertTriangle className="w-4 h-4" />
                  {analysis.urgency}
                </span>
              </div>
              <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                  Detected Device
                </span>
                <span className="text-base font-bold text-slate-100 mt-1 block">
                  {analysis.deviceType}
                </span>
              </div>
            </div>

            <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl text-sm text-slate-200 leading-relaxed">
              <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold block mb-1">
                Triaged Issue Summary:
              </span>
              "{analysis.summary}"
            </div>
          </div>

          {/* Execution Log */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-7 shadow-xl flex-1 flex flex-col font-mono text-sm">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
              <span className="font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <Terminal className="w-5 h-5 text-emerald-400" /> Automated
                Execution Trace
              </span>
              <span className="text-xs text-emerald-400 bg-emerald-950/60 px-2.5 py-1 rounded-md border border-emerald-800/50">
                Autonomous Mode: ON
              </span>
            </div>

            <div className="space-y-3 overflow-y-auto flex-1 pr-2">
              {logs.map((log) => (
                <div
                  key={log.id}
                  className="flex items-start space-x-3 py-2 border-b border-slate-800/60 last:border-0"
                >
                  <span className="text-slate-500 shrink-0 font-medium">
                    [{log.time}]
                  </span>
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                  <span className="text-slate-200 text-sm leading-snug">
                    {log.text}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
