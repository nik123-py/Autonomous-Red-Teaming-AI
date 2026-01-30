import React, { useState, useEffect } from 'react'
import axios from 'axios'
import AttackPathVisualization from '../components/AttackPathVisualization'
import './Pages.css'

const API_BASE = 'http://localhost:8003/api'

function SimulationPage() {
    const [currentState, setCurrentState] = useState(null)
    const [isSimulating, setIsSimulating] = useState(false)
    const [simulationResult, setSimulationResult] = useState(null)
    const [attackPath, setAttackPath] = useState(null)
    const [iterations, setIterations] = useState(100)
    const [targetHost, setTargetHost] = useState('')

    useEffect(() => {
        fetchState()
    }, [])

    const fetchState = async () => {
        try {
            const response = await axios.get(`${API_BASE}/state`)
            setCurrentState(response.data)
        } catch (error) {
            console.error('Failed to fetch state:', error)
        }
    }

    const startSimulation = async () => {
        setIsSimulating(true)
        setSimulationResult(null)
        setAttackPath(null)

        try {
            const response = await axios.post(`${API_BASE}/simulate`, {
                iterations,
                target_host: targetHost || null
            })

            setSimulationResult(response.data)
            setAttackPath(response.data.attack_path)
            await fetchState()
        } catch (error) {
            console.error('Simulation failed:', error)
            alert('Simulation failed: ' + (error.response?.data?.detail || error.message))
        } finally {
            setIsSimulating(false)
        }
    }

    const resetEnvironment = async () => {
        try {
            await axios.post(`${API_BASE}/reset`)
            setSimulationResult(null)
            setAttackPath(null)
            await fetchState()
        } catch (error) {
            console.error('Reset failed:', error)
        }
    }

    const accessLevelColors = {
        none: '#ff4444',
        public: '#ffaa00',
        internal: '#00aaff',
        admin: '#00ff88'
    }

    return (
        <div className="page">
            <div className="page-header">
                <h1 className="page-title">
                    <span className="page-title-icon">🤖</span>
                    AI Attack Simulation
                </h1>
                <p className="page-subtitle">Run autonomous attack simulation powered by Q-learning reinforcement learning</p>
            </div>

            {/* Configuration Card */}
            <div className="card animate-fade-in" style={{ marginBottom: '2rem' }}>
                <div className="card-header">
                    <h2 className="card-title">
                        <span>⚙️</span> Simulation Configuration
                    </h2>
                </div>

                <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
                    <div className="form-group">
                        <label className="form-label">Number of Iterations</label>
                        <input
                            type="number"
                            className="form-input"
                            value={iterations}
                            onChange={(e) => setIterations(parseInt(e.target.value) || 100)}
                            min="10"
                            max="500"
                            disabled={isSimulating}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Target Host (optional)</label>
                        <input
                            type="text"
                            className="form-input"
                            value={targetHost}
                            onChange={(e) => setTargetHost(e.target.value)}
                            placeholder="192.168.1.100 or example.com"
                            disabled={isSimulating}
                        />
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '1rem' }}>
                    <button
                        className="btn btn-primary btn-lg"
                        onClick={startSimulation}
                        disabled={isSimulating}
                    >
                        {isSimulating ? (
                            <>
                                <span className="loading-spinner"></span>
                                Running Simulation...
                            </>
                        ) : (
                            <>
                                <span>▶️</span>
                                Start Simulation
                            </>
                        )}
                    </button>
                    <button
                        className="btn btn-secondary"
                        onClick={resetEnvironment}
                        disabled={isSimulating}
                    >
                        <span>🔄</span>
                        Reset Environment
                    </button>
                </div>
            </div>

            {/* Current State Card */}
            {currentState && (
                <div className="card animate-fade-in" style={{ marginBottom: '2rem' }}>
                    <div className="card-header">
                        <h2 className="card-title">
                            <span>📊</span> Current State
                        </h2>
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
                            <div className="stat-value">{currentState.visited_components.length}</div>
                            <div className="stat-label">Components</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{currentState.discovered_vulnerabilities.length}</div>
                            <div className="stat-label">Vulnerabilities</div>
                        </div>
                    </div>
                </div>
            )}

            {/* Simulation Results */}
            {simulationResult && (
                <div className="card animate-fade-in" style={{ marginBottom: '2rem' }}>
                    <div className="card-header">
                        <h2 className="card-title">
                            <span>🎯</span> Simulation Results
                        </h2>
                        <span
                            className="badge"
                            style={{
                                background: `${accessLevelColors[simulationResult.final_access_level]}15`,
                                color: accessLevelColors[simulationResult.final_access_level]
                            }}
                        >
                            FINAL: {simulationResult.final_access_level.toUpperCase()}
                        </span>
                    </div>

                    <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: '#00ff88' }}>
                                {simulationResult.successful_attacks}
                            </div>
                            <div className="stat-label">Successful</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: '#ff4444' }}>
                                {simulationResult.failed_attacks}
                            </div>
                            <div className="stat-label">Failed</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{simulationResult.total_iterations}</div>
                            <div className="stat-label">Total Iterations</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{simulationResult.discovered_vulnerabilities.length}</div>
                            <div className="stat-label">Vulns Found</div>
                        </div>
                    </div>

                    {simulationResult.strategic_hint_used && (
                        <div style={{
                            padding: '1rem',
                            background: simulationResult.hint_success ? 'rgba(0, 255, 136, 0.1)' : 'rgba(255, 68, 68, 0.1)',
                            borderRadius: '8px',
                            border: `1px solid ${simulationResult.hint_success ? 'rgba(0, 255, 136, 0.2)' : 'rgba(255, 68, 68, 0.2)'}`,
                            marginBottom: '1rem'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <span>{simulationResult.hint_success ? '✅' : '❌'}</span>
                                <strong>Strategic Hint: </strong>
                                <span style={{ color: '#00d4ff' }}>
                                    {simulationResult.strategic_hint_used.replace(/_/g, ' ').toUpperCase()}
                                </span>
                                <span style={{ color: simulationResult.hint_success ? '#00ff88' : '#ff4444' }}>
                                    - {simulationResult.hint_success ? 'Successful!' : 'Failed'}
                                </span>
                            </div>
                        </div>
                    )}

                    {simulationResult.discovered_vulnerabilities.length > 0 && (
                        <div>
                            <h4 style={{ color: '#fff', marginBottom: '0.75rem' }}>Discovered Vulnerabilities</h4>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                                {simulationResult.discovered_vulnerabilities.map((vuln, idx) => (
                                    <span key={idx} className="badge badge-warning">{vuln}</span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Attack Path Visualization */}
            {attackPath && (
                <div className="animate-fade-in">
                    <AttackPathVisualization
                        attackPath={attackPath}
                        finalAccessLevel={simulationResult?.final_access_level}
                    />
                </div>
            )}
        </div>
    )
}

export default SimulationPage
