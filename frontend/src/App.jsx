import React from "react";
import ComplaintForm from "./components/ComplaintForm";
import CopilotPanel from "./components/CopilotPanel";

export default function App() {
  return (
    <div className="app-shell">
      <div className="app-grid">
        <main className="form-column">
          <ComplaintForm />
        </main>
        <aside className="copilot-column">
          <CopilotPanel />
        </aside>
      </div>
    </div>
  );
}
