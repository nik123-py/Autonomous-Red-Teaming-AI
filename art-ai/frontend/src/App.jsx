import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import {
  HomePage,
  SimulationPage,
  NetworkScanPage,
  VulnScanPage,
  ExploitGeneratorPage,
  CodeAnalysisPage,
  AttackHistoryPage,
  AutonomousSchedulerPage,
  PentestChatPage
} from './pages'
import './pages/Pages.css'
import './App.css'

function App() {
  return (
    <Router>
      <div className="app">
        <Navbar />
        <main className="app-main">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/simulation" element={<SimulationPage />} />
            <Route path="/network-scan" element={<NetworkScanPage />} />
            <Route path="/vuln-scan" element={<VulnScanPage />} />
            <Route path="/exploits" element={<ExploitGeneratorPage />} />
            <Route path="/code-analysis" element={<CodeAnalysisPage />} />
            <Route path="/attack-history" element={<AttackHistoryPage />} />
            <Route path="/autonomous" element={<AutonomousSchedulerPage />} />
            <Route path="/pentest-chat" element={<PentestChatPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
