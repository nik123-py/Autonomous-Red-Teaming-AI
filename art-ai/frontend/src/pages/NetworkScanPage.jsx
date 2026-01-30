import React, { useState } from 'react'
import axios from 'axios'
import './Pages.css'

const API_BASE = 'http://localhost:8003/api'

function NetworkScanPage() {
    const [target, setTarget] = useState('')
    const [scanning, setScanning] = useState(false)
    const [scanResults, setScanResults] = useState(null)

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
                scan_type: 'ports'
            })
            setScanResults(response.data)
        } catch (error) {
            console.error('Scan failed:', error)
            alert('Scan failed: ' + (error.response?.data?.detail || error.message))
        } finally {
            setScanning(false)
        }
    }

    return (
        <div className="page">
            <div className="page-header">
                <h1 className="page-title">
                    <span className="page-title-icon">🔍</span>
                    Network Scanner
                </h1>
                <p className="page-subtitle">Scan target hosts to discover open ports and running services</p>
            </div>

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
                            Scanning...
                        </>
                    ) : (
                        <>
                            <span>🔍</span>
                            Start Network Scan
                        </>
                    )}
                </button>
            </div>

            {/* Scan Results */}
            {scanResults && (
                <div className="card animate-fade-in">
                    <div className="card-header">
                        <h2 className="card-title">
                            <span>📊</span> Scan Results: {scanResults.target}
                        </h2>
                        <span className="badge badge-success">{scanResults.open_ports.length} Ports Found</span>
                    </div>

                    {/* Open Ports */}
                    {scanResults.open_ports.length > 0 ? (
                        <div className="results-list">
                            <h4 style={{ color: '#fff', marginBottom: '1rem' }}>Open Ports</h4>
                            {scanResults.open_ports.map((port, idx) => (
                                <div key={idx} className="result-item">
                                    <div className="result-item-header">
                                        <span className="result-item-title">
                                            <span style={{ color: '#00d4ff', fontWeight: 'bold', fontSize: '1.1rem' }}>
                                                {port.port}
                                            </span>
                                            <span style={{ color: '#6b7280', margin: '0 0.5rem' }}>/</span>
                                            <span style={{ color: '#00ff88' }}>{port.protocol || 'TCP'}</span>
                                        </span>
                                        <span className="badge badge-info">{port.state || 'OPEN'}</span>
                                    </div>
                                    <div style={{ color: '#9ca3af' }}>
                                        <strong>Service:</strong> {port.service || 'Unknown'}
                                        {port.version && <span style={{ marginLeft: '0.5rem' }}>({port.version})</span>}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="empty-state">
                            <div className="empty-state-icon">🔒</div>
                            <div className="empty-state-title">No Open Ports Found</div>
                            <p>The target appears to have all ports closed or filtered.</p>
                        </div>
                    )}

                    {/* Discovered Services */}
                    {scanResults.services && scanResults.services.length > 0 && (
                        <div style={{ marginTop: '2rem' }}>
                            <h4 style={{ color: '#fff', marginBottom: '1rem' }}>Discovered Services</h4>
                            <div className="results-list">
                                {scanResults.services.map((service, idx) => (
                                    <div key={idx} className="result-item">
                                        <div className="result-item-header">
                                            <span className="result-item-title" style={{ color: '#00d4ff' }}>
                                                {service.name}
                                            </span>
                                            <span className="badge badge-info">Port {service.port}</span>
                                        </div>
                                        <div style={{ color: '#9ca3af' }}>
                                            <strong>Protocol:</strong> {service.protocol || 'TCP'}
                                            {service.version && (
                                                <span style={{ marginLeft: '1rem' }}>
                                                    <strong>Version:</strong> {service.version}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

export default NetworkScanPage
