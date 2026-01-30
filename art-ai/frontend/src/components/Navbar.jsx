import React, { useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import axios from 'axios'
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
  MenuIcon,
  CloseIcon
} from './Icons'
import './Navbar.css'

const API_BASE = 'http://localhost:8003/api'

function Navbar() {
  const [isOpen, setIsOpen] = useState(false)
  const [backendStatus, setBackendStatus] = useState('checking')
  const location = useLocation()

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

  const navItems = [
    {
      section: 'Main',
      items: [
        { path: '/', Icon: DashboardIcon, label: 'Dashboard' },
        { path: '/simulation', Icon: AISimulationIcon, label: 'AI Simulation' },
        { path: '/autonomous', Icon: ScheduleIcon, label: 'Autonomous Scheduler' },
        { path: '/pentest-chat', Icon: ChatIcon, label: 'Pentest AI Assistant' },
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
      section: 'History',
      items: [
        { path: '/attack-history', Icon: AttackHistoryIcon, label: 'Attack Paths' },
      ]
    }
  ]

  return (
    <>
      <button 
        className="nav-toggle" 
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Toggle navigation"
      >
        {isOpen ? <CloseIcon size={20} color="#00d4ff" /> : <MenuIcon size={20} color="#00d4ff" />}
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
        </div>
      </nav>
    </>
  )
}

export default Navbar
