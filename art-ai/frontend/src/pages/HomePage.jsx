import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
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
  ChartIcon,
  LightbulbIcon
} from '../components/Icons'
import './Pages.css'

const API_BASE = 'http://localhost:8003/api'

function HomePage() {
    const [currentState, setCurrentState] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchState()
    }, [])

    const fetchState = async () => {
        try {
            const response = await axios.get(`${API_BASE}/state`)
            setCurrentState(response.data)
        } catch (error) {
            console.error('Failed to fetch state:', error)
        } finally {
            setLoading(false)
        }
    }

    const accessLevelColors = {
        none: '#ff4444',
        public: '#ffaa00',
        internal: '#00aaff',
        admin: '#00ff88'
    }

    const quickActions = [
        {
            path: '/simulation',
            Icon: AISimulationIcon,
            title: 'AI Simulation',
            desc: 'Run autonomous attack simulation with Q-learning agent'
        },
        {
            path: '/autonomous',
            Icon: ScheduleIcon,
            title: 'Autonomous Scheduler',
            desc: 'Schedule attacks every 10-20 min on target for continuous red teaming'
        },
        {
            path: '/pentest-chat',
            Icon: ChatIcon,
            title: 'Pentest AI Assistant',
            desc: 'Ask questions when stuck or request exploit generation'
        },
        {
            path: '/network-scan',
            Icon: NetworkScanIcon,
            title: 'Network Scanner',
            desc: 'Scan ports and discover services on target hosts'
        },
        {
            path: '/vuln-scan',
            Icon: VulnerabilityScanIcon,
            title: 'Vulnerability Scan',
            desc: 'Detect vulnerabilities with ML-powered analysis'
        },
        {
            path: '/code-analysis',
            Icon: CodeAnalysisIcon,
            title: 'Code Analysis',
            desc: 'Analyze C/C++ code for vulnerabilities with IVDetect'
        },
        {
            path: '/exploits',
            Icon: ExploitGeneratorIcon,
            title: 'Exploit Generator',
            desc: 'Generate custom exploits for discovered vulnerabilities'
        },
        {
            path: '/attack-history',
            Icon: AttackHistoryIcon,
            title: 'Attack History',
            desc: 'View past attack paths and simulation results'
        }
    ]

    if (loading) {
        return (
            <div className="page">
                <div className="empty-state">
                    <div className="loading-spinner"></div>
                    <p>Loading...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="page">
            <div className="page-header">
                <h1 className="page-title">
                    <span className="page-title-icon">
                        <DashboardIcon size={32} color="#00d4ff" />
                    </span>
                    Dashboard
                </h1>
                <p className="page-subtitle">Welcome to ART-AI - Autonomous Red Team Security Platform</p>
            </div>

            {/* Current State Stats */}
            {currentState && (
                <div className="card animate-fade-in" style={{ marginBottom: '2rem' }}>
                    <div className="card-header">
                        <h2 className="card-title">
                            <span className="card-title-icon">
                                <ChartIcon size={24} color="#00d4ff" />
                            </span>
                            Current Environment State
                        </h2>
                        <span
                            className="badge"
                            style={{
                                background: `${accessLevelColors[currentState.current_access_level]}15`,
                                color: accessLevelColors[currentState.current_access_level]
                            }}
                        >
                            {currentState.current_access_level.toUpperCase()}
                        </span>
                    </div>

                    <div className="grid-4">
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: accessLevelColors[currentState.current_access_level] }}>
                                {currentState.current_access_level.toUpperCase()}
                            </div>
                            <div className="stat-label">Access Level</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{currentState.iteration_count}</div>
                            <div className="stat-label">Iterations</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{currentState.discovered_services.length}</div>
                            <div className="stat-label">Services</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{currentState.discovered_vulnerabilities.length}</div>
                            <div className="stat-label">Vulnerabilities</div>
                        </div>
                    </div>

                    {currentState.hint_available === 1 && (
                        <div style={{
                            marginTop: '1.5rem',
                            padding: '1rem',
                            background: 'rgba(0, 212, 255, 0.1)',
                            borderRadius: '8px',
                            border: '1px solid rgba(0, 212, 255, 0.2)'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                <LightbulbIcon size={20} color="#00d4ff" />
                                <strong style={{ color: '#00d4ff' }}>Strategic Hint Available</strong>
                            </div>
                            <p style={{ color: '#9ca3af', margin: 0 }}>
                                Suggested Action: <span style={{ color: '#00ff88' }}>{currentState.strategic_hint?.replace(/_/g, ' ').toUpperCase()}</span>
                                {' '}({(currentState.hint_confidence * 100).toFixed(0)}% confidence)
                            </p>
                        </div>
                    )}
                </div>
            )}

            {/* Quick Actions */}
            <h2 style={{ color: '#fff', marginBottom: '1rem', fontSize: '1.25rem' }}>
                Quick Actions
            </h2>
            <div className="grid-3">
                {quickActions.map((action, idx) => {
                    const IconComponent = action.Icon
                    return (
                        <Link
                            key={idx}
                            to={action.path}
                            className="action-card animate-fade-in"
                            style={{ animationDelay: `${idx * 0.05}s` }}
                        >
                            <div className="action-card-icon">
                                <IconComponent size={32} color="#00d4ff" />
                            </div>
                            <div className="action-card-title">{action.title}</div>
                            <div className="action-card-desc">{action.desc}</div>
                        </Link>
                    )
                })}
            </div>
        </div>
    )
}

export default HomePage
