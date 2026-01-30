import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './Pages.css'

const API_BASE = 'http://localhost:8003/api'

function VulnScanPage() {
    const [target, setTarget] = useState('')
    const [scanning, setScanning] = useState(false)
    const [scanResults, setScanResults] = useState(null)
    const [mlModelStatus, setMlModelStatus] = useState(null)

    useEffect(() => {
        checkModelStatus()
    }, [])

    const checkModelStatus = async () => {
        try {
            const response = await axios.get(`${API_BASE}/model-status`)
            setMlModelStatus(response.data)
        } catch (error) {
            setMlModelStatus({ available: false })
        }
    }

    const handleScan = async () => {
        if (!target.trim()) {
            alert('Please enter a target')
            return
        }

        setScanning(true)
        setScanResults(null)

        try {
            const response = await axios.post(`${API_BASE}/scan`, {
                target: target.trim(),
                scan_type: 'full'
            })
            setScanResults(response.data)
        } catch (error) {
            console.error('Scan failed:', error)
            alert('Scan failed: ' + (error.response?.data?.detail || error.message))
        } finally {
            setScanning(false)
        }
    }

    const getSeverityColor = (severity) => {
        const colors = {
            critical: '#ff4444',
            high: '#ff8800',
            medium: '#ffaa00',
            low: '#00ff88'
        }
        return colors[severity] || '#6b7280'
    }

    return (
        <div className="page">
            <div className="page-header">
                <h1 className="page-title">
                    <span className="page-title-icon">🛡️</span>
                    Vulnerability Scanner
                </h1>
                <p className="page-subtitle">Scan targets for vulnerabilities with ML-powered detection</p>
            </div>

            {/* ML Model Status */}
            {mlModelStatus && (
                <div
                    className="card animate-fade-in"
                    style={{
                        marginBottom: '1.5rem',
                        background: mlModelStatus.available ? 'rgba(0, 255, 136, 0.05)' : 'rgba(255, 170, 0, 0.05)',
                        borderColor: mlModelStatus.available ? 'rgba(0, 255, 136, 0.2)' : 'rgba(255, 170, 0, 0.2)'
                    }}
                >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span style={{ fontSize: '1.5rem' }}>{mlModelStatus.available ? '🤖' : '⚠️'}</span>
                        <div>
                            <div style={{ color: '#fff', fontWeight: '600' }}>
                                ML Model: {mlModelStatus.available ? 'Active' : 'Unavailable'}
                            </div>
                            <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                                {mlModelStatus.available
                                    ? 'Using machine learning for enhanced vulnerability detection'
                                    : 'Using rule-based detection (install PyTorch to enable ML model)'
                                }
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Scan Configuration */}
            <div className="card animate-fade-in" style={{ marginBottom: '2rem' }}>
                <div className="card-header">
                    <h2 className="card-title">
                        <span>⚙️</span> Scan Configuration
                    </h2>
                </div>

                <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                    <label className="form-label">Target Host</label>
                    <input
                        type="text"
                        className="form-input"
                        value={target}
                        onChange={(e) => setTarget(e.target.value)}
                        placeholder="192.168.1.100 or example.com"
                        disabled={scanning}
                    />
                </div>

                <button
                    className="btn btn-primary btn-lg"
                    onClick={handleScan}
                    disabled={scanning || !target.trim()}
                >
                    {scanning ? (
                        <>
                            <span className="loading-spinner"></span>
                            Scanning for Vulnerabilities...
                        </>
                    ) : (
                        <>
                            <span>🛡️</span>
                            Start Vulnerability Scan
                        </>
                    )}
                </button>
            </div>

            {/* Scan Results */}
            {scanResults && (
                <>
                    {/* Summary Stats */}
                    <div className="card animate-fade-in" style={{ marginBottom: '2rem' }}>
                        <div className="card-header">
                            <h2 className="card-title">
                                <span>📊</span> Scan Summary: {scanResults.target}
                            </h2>
                        </div>
                        <div className="grid-4">
                            <div className="stat-card">
                                <div className="stat-value">{scanResults.open_ports.length}</div>
                                <div className="stat-label">Open Ports</div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-value">{scanResults.services.length}</div>
                                <div className="stat-label">Services</div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-value" style={{ color: '#ff4444' }}>
                                    {scanResults.vulnerabilities.length}
                                </div>
                                <div className="stat-label">Vulnerabilities</div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-value">
                                    {scanResults.vulnerabilities.filter(v => v.detection_method === 'ML Model').length}
                                </div>
                                <div className="stat-label">ML Detections</div>
                            </div>
                        </div>
                    </div>

                    {/* Vulnerabilities */}
                    <div className="card animate-fade-in">
                        <div className="card-header">
                            <h2 className="card-title">
                                <span>🔓</span> Discovered Vulnerabilities
                            </h2>
                        </div>

                        {scanResults.vulnerabilities.length > 0 ? (
                            <div className="results-list">
                                {scanResults.vulnerabilities.map((vuln, idx) => (
                                    <div key={idx} className="result-item">
                                        <div className="result-item-header">
                                            <span className="result-item-title">
                                                {vuln.name}
                                                {vuln.detection_method === 'ML Model' && (
                                                    <span
                                                        style={{
                                                            marginLeft: '0.5rem',
                                                            background: 'rgba(0, 212, 255, 0.15)',
                                                            color: '#00d4ff',
                                                            padding: '0.2rem 0.5rem',
                                                            borderRadius: '4px',
                                                            fontSize: '0.7rem'
                                                        }}
                                                    >
                                                        🤖 ML
                                                    </span>
                                                )}
                                            </span>
                                            <span
                                                className="badge"
                                                style={{
                                                    background: `${getSeverityColor(vuln.severity)}15`,
                                                    color: getSeverityColor(vuln.severity)
                                                }}
                                            >
                                                {vuln.severity.toUpperCase()}
                                            </span>
                                        </div>

                                        {vuln.cve_id && (
                                            <div style={{ marginBottom: '0.5rem' }}>
                                                <span className="badge badge-info">{vuln.cve_id}</span>
                                            </div>
                                        )}

                                        <p style={{ color: '#9ca3af', marginBottom: '0.75rem' }}>{vuln.description}</p>

                                        <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>
                                            <div><strong>Service:</strong> {vuln.affected_service}{vuln.affected_port && `:${vuln.affected_port}`}</div>
                                            {vuln.confidence && (
                                                <div><strong>Confidence:</strong> {(vuln.confidence * 100).toFixed(0)}%</div>
                                            )}
                                            {vuln.exploit_available && (
                                                <div style={{ color: '#ff8800', marginTop: '0.5rem' }}>
                                                    ⚠️ Exploit Available
                                                </div>
                                            )}
                                        </div>

                                        <div style={{
                                            marginTop: '0.75rem',
                                            padding: '0.75rem',
                                            background: 'rgba(0, 255, 136, 0.05)',
                                            borderRadius: '6px',
                                            fontSize: '0.85rem'
                                        }}>
                                            <strong style={{ color: '#00ff88' }}>Remediation:</strong>
                                            <span style={{ color: '#9ca3af', marginLeft: '0.5rem' }}>{vuln.remediation}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="empty-state">
                                <div className="empty-state-icon">✅</div>
                                <div className="empty-state-title">No Vulnerabilities Found</div>
                                <p>The target appears to be secure based on this scan.</p>
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    )
}

export default VulnScanPage
