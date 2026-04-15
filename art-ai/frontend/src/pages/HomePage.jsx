import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { useTier, ROUTE_TIER_MAP } from '../components/TierContext'
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
    const { hasAccess } = useTier()

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
        none: '#ef4444',
        public: '#f59e0b',
        internal: '#3b82f6',
        admin: '#22c55e'
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

    // Filter actions by the user's tier
    const filteredActions = quickActions.filter(action => {
        const minTier = ROUTE_TIER_MAP[action.path]
        return !minTier || hasAccess(minTier)
    })

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
                        <DashboardIcon size={32} color="#ef4444" />
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
                                <ChartIcon size={24} color="#ef4444" />
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
                            <div className="stat-value" style={{ color: accessLevelColors[currentState.current_access_level] || '#ef4444' }}>
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
                            background: 'rgba(239, 68, 68, 0.08)',
                            borderRadius: '8px',
                            border: '1px solid rgba(239, 68, 68, 0.15)'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                <LightbulbIcon size={20} color="#ef4444" />
                                <strong style={{ color: '#ef4444' }}>Strategic Hint Available</strong>
                            </div>
                            <p style={{ color: '#94a3b8', margin: 0 }}>
                                Suggested Action: <span style={{ color: '#22c55e' }}>{currentState.strategic_hint?.replace(/_/g, ' ').toUpperCase()}</span>
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
                {filteredActions.map((action, idx) => {
                    const IconComponent = action.Icon
                    return (
                        <Link
                            key={idx}
                            to={action.path}
                            className="action-card animate-fade-in"
                            style={{ animationDelay: `${idx * 0.05}s` }}
                        >
                            <div className="action-card-icon">
                                <IconComponent size={32} color="#ef4444" />
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
