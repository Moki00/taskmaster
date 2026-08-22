import React, { useState } from "react";
import {
  Terminal,
  Send,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Server,
  Calendar,
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

  // Live Agent State
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
    }, 1200);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-6 md:p-10 flex flex-col">
      {/* Top Header */}
      <header className="flex items-center justify-between pb-6 border-b border-slate-800 mb-8">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">
              TASKMASTER{" "}
              <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full ml-2">
                AGENT ACTIVE
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Autonomous IT Client Dispatch & Triage Coordinator
            </p>
          </div>
        </div>
        <div className="text-xs text-slate-500 font-mono flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>Google GenAI SDK · Gemini 3.5 Flash</span>
        </div>
      </header>

      {/* Main Split Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 flex-1">
        {/* Left Side: Client Simulator */}
        <div className="lg:col-span-5 flex flex-col justify-between bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 shadow-xl backdrop-blur-sm">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-6">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-emerald-400" /> Inbound
                Client Channel
              </span>
              <span className="text-xs font-mono text-slate-500">
                Channel: Web Intake / SMS
              </span>
            </div>

            {/* Presets */}
            <div className="mb-4">
              <label className="text-xs text-slate-400 block mb-2 font-medium">
                Quick Presets:
              </label>
              <div className="flex flex-col gap-2">
                {PRESET_MESSAGES.map((msg, idx) => (
                  <button
                    key={idx}
                    onClick={() => setInputMessage(msg)}
                    className="text-left text-xs bg-slate-800/50 hover:bg-slate-800 border border-slate-700/60 p-2.5 rounded-lg text-slate-300 transition-colors line-clamp-1"
                  >
                    "{msg}"
                  </button>
                ))}
              </div>
            </div>

            {/* Client Info Inputs */}
            <div className="space-y-4 my-4">
              <div>
                <label className="text-xs text-slate-400 block mb-1">
                  Client Name
                </label>
                <input
                  type="text"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">
                  Unstructured Issue Description
                </label>
                <textarea
                  rows={4}
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 focus:outline-none focus:border-emerald-500 font-sans"
                  placeholder="Describe your issue..."
                />
              </div>
            </div>
          </div>

          <button
            onClick={handleSimulate}
            disabled={isProcessing}
            className="w-full py-3 px-4 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white font-medium rounded-xl transition flex items-center justify-center gap-2 text-sm shadow-lg shadow-emerald-950"
          >
            {isProcessing ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            {isProcessing
              ? "Agent Orchestrating..."
              : "Simulate Incoming Request"}
          </button>
        </div>

        {/* Right Side: Taskmaster Mission Control */}
        <div className="lg:col-span-7 flex flex-col space-y-6">
          {/* AI Structured Extraction Box */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 shadow-xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <Server className="w-4 h-4 text-emerald-400" /> AI Extraction &
                Context Analysis
              </span>
              <div className="flex items-center gap-1.5 text-xs font-mono text-slate-400">
                <Clock className="w-3.5 h-3.5" />
                <span>{analysis.timestamp}</span>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
              <div className="bg-slate-950/80 border border-slate-800 p-3 rounded-xl">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider block">
                  Category
                </span>
                <span className="text-sm font-semibold text-slate-200 mt-1 block">
                  {analysis.category}
                </span>
              </div>
              <div className="bg-slate-950/80 border border-slate-800 p-3 rounded-xl">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider block">
                  Urgency Rating
                </span>
                <span
                  className={`text-sm font-semibold mt-1 inline-flex items-center gap-1.5 ${
                    analysis.urgency.includes("Critical")
                      ? "text-rose-400"
                      : "text-amber-400"
                  }`}
                >
                  <AlertTriangle className="w-3.5 h-3.5" />
                  {analysis.urgency}
                </span>
              </div>
              <div className="bg-slate-950/80 border border-slate-800 p-3 rounded-xl col-span-2 md:col-span-1">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider block">
                  Detected Device
                </span>
                <span className="text-sm font-semibold text-slate-200 mt-1 block">
                  {analysis.deviceType}
                </span>
              </div>
            </div>

            <div className="bg-slate-950/60 border border-slate-800/60 p-3 rounded-xl text-xs text-slate-300">
              <span className="text-slate-500 font-semibold block mb-1">
                Triaged Issue Summary:
              </span>
              "{analysis.summary}"
            </div>
          </div>

          {/* Autonomous Execution Log (Trace) */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 shadow-xl flex-1 flex flex-col font-mono text-xs">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
              <span className="font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <Terminal className="w-4 h-4 text-emerald-400" /> Automated
                Execution Trace
              </span>
              <span className="text-[11px] text-emerald-400/80 bg-emerald-950/50 px-2 py-0.5 rounded border border-emerald-800/40">
                Autonomous Mode: ON
              </span>
            </div>

            <div className="space-y-2.5 overflow-y-auto flex-1 pr-1">
              {logs.map((log) => (
                <div
                  key={log.id}
                  className="flex items-start space-x-3 py-1.5 border-b border-slate-800/40 last:border-0"
                >
                  <span className="text-slate-500 select-none">
                    [{log.time}]
                  </span>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span className="text-slate-200">{log.text}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
