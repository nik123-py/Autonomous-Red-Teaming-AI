import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Navbar from './components/Navbar'
import { TierProvider, useTier, ROUTE_TIER_MAP } from './components/TierContext'
import {
  HomePage,
  SimulationPage,
  NetworkScanPage,
  VulnScanPage,
  ExploitGeneratorPage,
  CodeAnalysisPage,
  AttackHistoryPage,
  AutonomousSchedulerPage,
  PentestChatPage,
  RLAgentPage,
  ComplianceDashboardPage,
  ReportGenerationPage,
  QuantumDefenderPage,
  OnboardingWizardPage,
  IntroductionPage
} from './pages'
import './pages/Pages.css'
import './App.css'

/** Wraps a route element — redirects to /dashboard if user lacks tier access */
function TierGate({ minTier, children }) {
  const { hasAccess, tier } = useTier()
  if (!tier) return <Navigate to="/" replace />
  if (!hasAccess(minTier)) return <Navigate to="/dashboard" replace />
  return children
}

/** Layout shell — hides Navbar on intro & assessment pages */
function AppShell() {
  const location = useLocation()
  const hideNavbar = location.pathname === '/' || location.pathname === '/userassessment'

  return (
    <div className="app">
      {!hideNavbar && <Navbar />}
      <main className={hideNavbar ? '' : 'app-main'}>
        <Routes>
          {/* Public pages — no navbar, no gate */}
          <Route path="/" element={<IntroductionPage />} />
          <Route path="/userassessment" element={<OnboardingWizardPage />} />

          {/* Essential tier */}
          <Route path="/dashboard" element={<TierGate minTier="essential"><HomePage /></TierGate>} />
          <Route path="/network-scan" element={<TierGate minTier="essential"><NetworkScanPage /></TierGate>} />
          <Route path="/vuln-scan" element={<TierGate minTier="essential"><VulnScanPage /></TierGate>} />
          <Route path="/code-analysis" element={<TierGate minTier="essential"><CodeAnalysisPage /></TierGate>} />
          <Route path="/compliance" element={<TierGate minTier="essential"><ComplianceDashboardPage /></TierGate>} />
          <Route path="/reports" element={<TierGate minTier="essential"><ReportGenerationPage /></TierGate>} />
          <Route path="/attack-history" element={<TierGate minTier="essential"><AttackHistoryPage /></TierGate>} />

          {/* Advanced tier */}
          <Route path="/exploits" element={<TierGate minTier="advanced"><ExploitGeneratorPage /></TierGate>} />
          <Route path="/pentest-chat" element={<TierGate minTier="advanced"><PentestChatPage /></TierGate>} />

          {/* Elite tier */}
          <Route path="/simulation" element={<TierGate minTier="elite"><SimulationPage /></TierGate>} />
          <Route path="/rl-agent" element={<TierGate minTier="elite"><RLAgentPage /></TierGate>} />
          <Route path="/autonomous" element={<TierGate minTier="elite"><AutonomousSchedulerPage /></TierGate>} />
          <Route path="/quantumdefender" element={<TierGate minTier="elite"><QuantumDefenderPage /></TierGate>} />

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}

function App() {
  return (
    <Router>
      <TierProvider>
        <AppShell />
      </TierProvider>
    </Router>
  )
}

export default App
