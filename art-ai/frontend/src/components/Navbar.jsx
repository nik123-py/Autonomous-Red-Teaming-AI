import React, { useState, useEffect } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useTier, ROUTE_TIER_MAP } from './TierContext'
import { 
  DashboardIcon, 
  AISimulationIcon, 
  NetworkScanIcon, 
  VulnerabilityScanIcon, 
  ExploitGeneratorIcon, 
  CodeAnalysisIcon, 
  AttackHistoryIcon,
  ScheduleIcon,
  ChatIcon,
  RLAgentIcon,
  ShieldIcon,
  DocumentIcon,
  MenuIcon,
  CloseIcon
} from './Icons'
import './Navbar.css'

const API_BASE = 'http://localhost:8003/api'

function Navbar() {
  const [isOpen, setIsOpen] = useState(false)
  const [backendStatus, setBackendStatus] = useState('checking')
  const location = useLocation()
  const navigate = useNavigate()
  const { hasAccess, clearTier, tier } = useTier()

  useEffect(() => {
    const checkBackend = async () => {
      try {
        await axios.get(`${API_BASE.replace('/api', '')}/`)
        setBackendStatus('online')
      } catch (error) {
        setBackendStatus('offline')
      }
    }
    checkBackend()
    const interval = setInterval(checkBackend, 30000)
    return () => clearInterval(interval)
  }, [])

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setIsOpen(false)
  }, [location])

  const allNavItems = [
    {
      section: 'Main',
      items: [
        { path: '/dashboard', Icon: DashboardIcon, label: 'Dashboard' },
        { path: '/simulation', Icon: AISimulationIcon, label: 'AI Simulation' },
        { path: '/rl-agent', Icon: RLAgentIcon, label: 'RL Agent Performance' },
        { path: '/autonomous', Icon: ScheduleIcon, label: 'Autonomous Scheduler' },
        { path: '/pentest-chat', Icon: ChatIcon, label: 'Pentest AI Assistant' },
        { path: '/quantumdefender', Icon: ChatIcon, label: 'QuantumDefender Automation' },
      ]
    },
    {
      section: 'Security Tools',
      items: [
        { path: '/network-scan', Icon: NetworkScanIcon, label: 'Network Scanner' },
        { path: '/vuln-scan', Icon: VulnerabilityScanIcon, label: 'Vulnerability Scan' },
        { path: '/exploits', Icon: ExploitGeneratorIcon, label: 'Exploit Generator' },
        { path: '/code-analysis', Icon: CodeAnalysisIcon, label: 'Code Analysis' },
      ]
    },
    {
      section: 'Reports & Compliance',
      items: [
        { path: '/compliance', Icon: ShieldIcon, label: 'Compliance Dashboard' },
        { path: '/reports', Icon: DocumentIcon, label: 'Report Generation' },
        { path: '/attack-history', Icon: AttackHistoryIcon, label: 'Attack Paths' },
      ]
    }
  ]

  // Filter nav items — only show links the user's tier can access
  const navItems = allNavItems.map(section => ({
    ...section,
    items: section.items.filter(item => {
      const minTier = ROUTE_TIER_MAP[item.path]
      return !minTier || hasAccess(minTier)
    })
  })).filter(section => section.items.length > 0)

  const handleReassess = () => {
    clearTier()
    navigate('/')
  }

  return (
    <>
      <button 
        className="nav-toggle" 
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Toggle navigation"
      >
        {isOpen ? <CloseIcon size={20} color="#ef4444" /> : <MenuIcon size={20} color="#ef4444" />}
      </button>

      <nav className={`nav-sidebar ${isOpen ? 'open' : ''}`}>
        <div className="nav-logo">
          <h1>ART-AI</h1>
          <p>Autonomous Red Team</p>
        </div>

        <div className="nav-menu">
          {navItems.map((section, idx) => (
            <div key={idx} className="nav-section">
              <div className="nav-section-title">{section.section}</div>
              {section.items.map((item) => {
                const IconComponent = item.Icon
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) => 
                      `nav-link ${isActive ? 'active' : ''}`
                    }
                  >
                    <span className="nav-link-icon">
                      <IconComponent size={20} color="currentColor" />
                    </span>
                    <span className="nav-link-text">{item.label}</span>
                  </NavLink>
                )
              })}
            </div>
          ))}
        </div>

        <div className="nav-footer">
          <div className="nav-status">
            <span className={`nav-status-dot ${backendStatus !== 'online' ? 'offline' : ''}`}></span>
            <span>Backend: {backendStatus === 'online' ? 'Connected' : backendStatus === 'offline' ? 'Offline' : 'Checking...'}</span>
          </div>
          {tier && (
            <button
              className="nav-reassess-btn"
              onClick={handleReassess}
              title="Re-run security assessment"
            >
              ↻ Re-assess Plan
            </button>
          )}
        </div>
      </nav>
    </>
  )
}

export default Navbar

