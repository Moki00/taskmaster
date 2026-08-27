import React, { useState } from "react";
import { Cpu } from "lucide-react";
import ChannelSimulator from "./components/ChannelSimulator";
import ExecutionLog from "./components/ExecutionLog";
import TicketSummary from "./components/TicketSummary";
import TurtleShellIcon from "./components/TurtleShellIcon";

const PRESET_MESSAGES = [
  "Our main switch is down and the office network is completely dead! We have clients arriving in 20 minutes!",
  "My laptop screen is flickering blue and won't boot into Windows after the update.",
  "Looking to get a quote on setting up a new mesh Wi-Fi network for our small warehouse.",
];

const INITIAL_ANALYSIS = {
  timestamp: "2026-08-22 15:04:12 UTC",
  client: "Alice Smith",
  category: "Network / Infrastructure",
  urgency: "Critical / High",
  deviceType: "Enterprise Switch / Gateway",
  summary: "Complete local area network failure affecting office operations.",
};

const INITIAL_LOGS = [
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
];

const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  "https://taskmaster-backend-735344105233.us-east1.run.app";

export default function TaskmasterVisualizer() {
  const [inputMessage, setInputMessage] = useState(PRESET_MESSAGES[0]);
  const [clientName, setClientName] = useState("Alice Smith");
  const [isProcessing, setIsProcessing] = useState(false);
  const [analysis, setAnalysis] = useState(INITIAL_ANALYSIS);
  const [logs, setLogs] = useState(INITIAL_LOGS);

  const handleSimulate = async () => {
    setIsProcessing(true);
    setLogs([]);

    try {
      const response = await fetch(`${API_BASE_URL}/api/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_name: clientName,
          message: inputMessage,
        }),
      });

      if (!response.ok) throw new Error(`API error: ${response.status}`);

      const data = await response.json();
      setAnalysis({
        timestamp: data.timestamp,
        client: data.client,
        category: data.category,
        urgency: data.urgency,
        deviceType: data.device_type,
        summary: data.summary,
        ticketNumber: data.ticket_number,
        draftReply: data.draft_reply,
      });
      setLogs(data.logs.map((log) => ({ ...log, id: Number(log.id) })));
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unknown request error";
      setLogs([
        {
          id: 1,
          time: new Date().toLocaleTimeString(),
          text: `Request failed: ${message}`,
          status: "error",
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-6 md:p-10 flex flex-col justify-between">
      <header className="flex items-center justify-between pb-6 border-b border-slate-800 mb-8">
        <div className="flex items-center space-x-4">
          <div className="w-14 h-14 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <TurtleShellIcon />
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
              Autonomous IT Client Dispatch &amp; Triage Coordinator
            </p>
          </div>
        </div>
        <div className="hidden md:flex text-sm text-slate-400 font-mono items-center space-x-2 bg-slate-900 px-4 py-2 rounded-lg border border-slate-800">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <span>Google GenAI SDK · Gemini 3.5 Flash</span>
        </div>
      </header>
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 flex-1">
        <ChannelSimulator
          clientName={clientName}
          inputMessage={inputMessage}
          isProcessing={isProcessing}
          presets={PRESET_MESSAGES}
          onClientNameChange={setClientName}
          onMessageChange={setInputMessage}
          onSimulate={handleSimulate}
        />
        <div className="lg:col-span-7 flex flex-col space-y-6">
          <TicketSummary analysis={analysis} />
          <ExecutionLog logs={logs} isProcessing={isProcessing} />
        </div>
      </div>
    </div>
  );
}
