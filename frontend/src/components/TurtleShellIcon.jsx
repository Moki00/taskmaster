import React from "react";

export default function TurtleShellIcon({
  className = "w-10 h-10 text-emerald-400",
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {/* Outer Shell Rim */}
      <path d="M12 2C6.5 2 3 6.5 3 12c0 5 3.5 9.5 9 10 5.5-.5 9-5 9-10 0-5.5-3.5-10-9-10z" />
      {/* Central Scute / Hexagon */}
      <polygon points="12,6 16,8.5 16,13.5 12,16 8,13.5 8,8.5" />
      {/* Radiating Shell Seams */}
      <line x1="12" y1="2" x2="12" y2="6" />
      <line x1="16" y1="8.5" x2="20.5" y2="7.5" />
      <line x1="16" y1="13.5" x2="20.5" y2="15" />
      <line x1="12" y1="16" x2="12" y2="22" />
      <line x1="8" y1="13.5" x2="3.5" y2="15" />
      <line x1="8" y1="8.5" x2="3.5" y2="7.5" />
    </svg>
  );
}
