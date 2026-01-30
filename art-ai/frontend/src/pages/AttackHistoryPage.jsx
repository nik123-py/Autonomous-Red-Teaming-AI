import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './Pages.css'

const API_BASE = 'http://localhost:8003/api'

function AttackHistoryPage() {
    const [attackPaths, setAttackPaths] = useState([])
    const [bestPath, setBestPath] = useState(null)
    const [loading, setLoading] = useState(true)
    const [selectedPath, setSelectedPath] = useState(null)

    useEffect(() => {
        fetchData()
    }, [])

    const fetchData = async () => {
        setLoading(true)
        try {
            const [pathsResponse, bestResponse] = await Promise.all([
                axios.get(`${API_BASE}/attack-paths`),
                axios.get(`${API_BASE}/best-path`).catch(() => ({ data: null }))
            ])
            setAttackPaths(pathsResponse.data.paths || [])
            setBestPath(bestResponse.data)
        } catch (error) {
            console.error('Failed to fetch attack paths:', error)
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

    if (loading) {
        return (
            <div className="page">
                <div className="page-header">
                    <h1 className="page-title">
                        <span className="page-title-icon">📊</span>
                        Attack History
                    </h1>
                </div>
                <div className="empty-state">
                    <div className="loading-spinner"></div>
                    <p>Loading attack paths...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="page">
            <div className="page-header">
                <h1 className="page-title">
                    <span className="page-title-icon">📊</span>
                    Attack History
                </h1>
                <p className="page-subtitle">View past attack simulations and their results</p>
            </div>

            {/* Best Path Highlight */}
            {bestPath && (
                <div
                    className="card animate-fade-in"
                    style={{
                        marginBottom: '2rem',
                        background: 'linear-gradient(135deg, rgba(0, 255, 136, 0.05), rgba(0, 212, 255, 0.05))',
                        borderColor: 'rgba(0, 255, 136, 0.2)'
                    }}
                >
                    <div className="card-header">
                        <h2 className="card-title">
                            <span>🏆</span> Best Attack Path
                        </h2>
                        <span
                            className="badge"
                            style={{
                                background: `${accessLevelColors[bestPath.final_access_level]}15`,
                                color: accessLevelColors[bestPath.final_access_level]
                            }}
                        >
                            {bestPath.final_access_level?.toUpperCase() || 'UNKNOWN'}
                        </span>
                    </div>

                    <div className="grid-4">
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: accessLevelColors[bestPath.final_access_level] }}>
                                {bestPath.final_access_level?.toUpperCase() || 'N/A'}
                            </div>
                            <div className="stat-label">Final Access</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{bestPath.attack_path?.length || 0}</div>
                            <div className="stat-label">Steps</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: '#00ff88' }}>
                                {bestPath.attack_path?.filter(a => a.success).length || 0}
                            </div>
                            <div className="stat-label">Successful</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{bestPath.vulnerabilities?.length || 0}</div>
                            <div className="stat-label">Vulns Found</div>
                        </div>
                    </div>

                    {bestPath.vulnerabilities && bestPath.vulnerabilities.length > 0 && (
                        <div style={{ marginTop: '1rem' }}>
                            <strong style={{ color: '#9ca3af', fontSize: '0.85rem' }}>Discovered Vulnerabilities:</strong>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.5rem' }}>
                                {bestPath.vulnerabilities.map((vuln, idx) => (
                                    <span key={idx} className="badge badge-warning">{vuln}</span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* All Attack Paths */}
            <div className="card animate-fade-in">
                <div className="card-header">
                    <h2 className="card-title">
                        <span>📋</span> All Attack Paths
                    </h2>
                    <button className="btn btn-secondary" onClick={fetchData}>
                        <span>🔄</span> Refresh
                    </button>
                </div>

                {attackPaths.length > 0 ? (
                    <div className="results-list">
                        {attackPaths.map((path, idx) => (
                            <div
                                key={path.id || idx}
                                className="result-item"
                                style={{ cursor: 'pointer' }}
                                onClick={() => setSelectedPath(selectedPath === idx ? null : idx)}
                            >
                                <div className="result-item-header">
                                    <span className="result-item-title">
                                        <span style={{ color: '#6b7280', marginRight: '0.5rem' }}>#{path.id || idx + 1}</span>
                                        Attack Path
                                        <span style={{
                                            marginLeft: '0.5rem',
                                            color: accessLevelColors[path.final_access_level]
                                        }}>
                                            → {path.final_access_level?.toUpperCase() || 'UNKNOWN'}
                                        </span>
                                    </span>
                                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                        <span style={{ color: '#6b7280', fontSize: '0.8rem' }}>
                                            {path.attack_path?.length || 0} steps
                                        </span>
                                        <span
                                            className="badge"
                                            style={{
                                                background: `${accessLevelColors[path.final_access_level]}15`,
                                                color: accessLevelColors[path.final_access_level]
                                            }}
                                        >
                                            {path.final_access_level?.toUpperCase() || 'UNKNOWN'}
                                        </span>
                                        <span style={{ color: '#6b7280' }}>
                                            {selectedPath === idx ? '▲' : '▼'}
                                        </span>
                                    </div>
                                </div>

                                {path.created_at && (
                                    <div style={{ color: '#6b7280', fontSize: '0.8rem', marginBottom: '0.5rem' }}>
                                        {new Date(path.created_at).toLocaleString()}
                                    </div>
                                )}

                                {/* Expanded Path Details */}
                                {selectedPath === idx && path.attack_path && (
                                    <div style={{
                                        marginTop: '1rem',
                                        paddingTop: '1rem',
                                        borderTop: '1px solid rgba(255, 255, 255, 0.1)'
                                    }}>
                                        <h4 style={{ color: '#fff', marginBottom: '0.75rem', fontSize: '0.9rem' }}>
                                            Attack Sequence
                                        </h4>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                            {path.attack_path.slice(0, 20).map((step, stepIdx) => (
                                                <div
                                                    key={stepIdx}
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '0.75rem',
                                                        padding: '0.5rem',
                                                        background: step.success ? 'rgba(0, 255, 136, 0.05)' : 'rgba(255, 68, 68, 0.05)',
                                                        borderRadius: '6px',
                                                        fontSize: '0.85rem'
                                                    }}
                                                >
                                                    <span style={{ color: '#6b7280', width: '30px' }}>#{step.iteration}</span>
                                                    <span style={{ color: step.success ? '#00ff88' : '#ff4444' }}>
                                                        {step.success ? '✓' : '✗'}
                                                    </span>
                                                    <span style={{ color: '#00d4ff' }}>
                                                        {step.action?.replace(/_/g, ' ').toUpperCase()}
                                                    </span>
                                                    <span style={{ color: '#6b7280', marginLeft: 'auto' }}>
                                                        → {step.access_level?.toUpperCase()}
                                                    </span>
                                                </div>
                                            ))}
                                            {path.attack_path.length > 20 && (
                                                <div style={{ color: '#6b7280', textAlign: 'center', fontSize: '0.85rem' }}>
                                                    ... and {path.attack_path.length - 20} more steps
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="empty-state">
                        <div className="empty-state-icon">📭</div>
                        <div className="empty-state-title">No Attack Paths Yet</div>
                        <p>Run a simulation to generate attack paths.</p>
                    </div>
                )}
            </div>
        </div>
    )
}

export default AttackHistoryPage
