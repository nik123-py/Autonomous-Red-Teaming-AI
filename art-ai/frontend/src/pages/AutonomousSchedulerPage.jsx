import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import AttackPathVisualization from '../components/AttackPathVisualization'
import './Pages.css'

const API_BASE = 'http://localhost:8003/api'

// Random interval between 10 and 20 minutes (in ms)
function getNextIntervalMs() {
    const minMs = 10 * 60 * 1000
    const maxMs = 20 * 60 * 1000
    return Math.floor(Math.random() * (maxMs - minMs + 1)) + minMs
}

function formatCountdown(ms) {
    const totalSeconds = Math.floor(ms / 1000)
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

function AutonomousSchedulerPage() {
    const [targetHost, setTargetHost] = useState('')
    const [iterationsPerRun, setIterationsPerRun] = useState(50)
    const [isRunning, setIsRunning] = useState(false)
    const [countdownMs, setCountdownMs] = useState(null)
    const [lastResult, setLastResult] = useState(null)
    const [runLog, setRunLog] = useState([])
    const [currentState, setCurrentState] = useState(null)
    const timerRef = useRef(null)
    const countdownRef = useRef(null)
    const isRunningRef = useRef(false)
    isRunningRef.current = isRunning

    useEffect(() => {
        fetchState()
    }, [])

    useEffect(() => {
        if (!isRunning) return
        const tick = () => {
            setCountdownMs((prev) => {
                if (prev == null) return null
                const next = prev - 1000
                if (next <= 0) return null
                return next
            })
        }
        const id = setInterval(tick, 1000)
        countdownRef.current = id
        return () => clearInterval(id)
    }, [isRunning])

    const fetchState = async () => {
        try {
            const response = await axios.get(`${API_BASE}/state`)
            setCurrentState(response.data)
        } catch (error) {
            console.error('Failed to fetch state:', error)
        }
    }

    const runScheduledAttack = async () => {
        try {
            const response = await axios.post(`${API_BASE}/simulate`, {
                iterations: iterationsPerRun,
                target_host: targetHost.trim() || null
            })
            setLastResult(response.data)
            setRunLog((prev) => [
                {
                    time: new Date().toLocaleTimeString(),
                    success: response.data.successful_attacks,
                    failed: response.data.failed_attacks,
                    finalAccess: response.data.final_access_level
                },
                ...prev.slice(0, 49)
            ])
            await fetchState()
        } catch (error) {
            console.error('Scheduled attack failed:', error)
            setRunLog((prev) => [
                { time: new Date().toLocaleTimeString(), error: error.response?.data?.detail || error.message },
                ...prev.slice(0, 49)
            ])
        }
    }

    const scheduleNext = useRef(() => {})
    scheduleNext.current = () => {
        const intervalMs = getNextIntervalMs()
        setCountdownMs(intervalMs)
        timerRef.current = setTimeout(async () => {
            await runScheduledAttack()
            if (isRunningRef.current) scheduleNext.current()
        }, intervalMs)
    }

    useEffect(() => {
        if (!isRunning) {
            if (timerRef.current) clearTimeout(timerRef.current)
            if (countdownRef.current) clearInterval(countdownRef.current)
            setCountdownMs(null)
            return
        }
        scheduleNext.current()
        return () => {
            if (timerRef.current) clearTimeout(timerRef.current)
        }
    }, [isRunning])

    const startAutonomous = () => setIsRunning(true)
    const stopAutonomous = () => setIsRunning(false)

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
                    <span className="page-title-icon">[+]</span>
                    Autonomous Attack Scheduler
                </h1>
                <p className="page-subtitle">
                    Schedule attacks every 10–20 minutes on a target for continuous red teaming
                </p>
            </div>

            {/* Configuration */}
            <div className="card animate-fade-in" style={{ marginBottom: '2rem' }}>
                <div className="card-header">
                    <h2 className="card-title">
                        <span>[*]</span> Scheduler Configuration
                    </h2>
                </div>
                <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
                    <div className="form-group">
                        <label className="form-label">Target Host (optional)</label>
                        <input
                            type="text"
                            className="form-input"
                            value={targetHost}
                            onChange={(e) => setTargetHost(e.target.value)}
                            placeholder="192.168.1.100 or example.com"
                            disabled={isRunning}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Iterations per attack run</label>
                        <input
                            type="number"
                            className="form-input"
                            value={iterationsPerRun}
                            onChange={(e) => setIterationsPerRun(parseInt(e.target.value) || 50)}
                            min="10"
                            max="200"
                            disabled={isRunning}
                        />
                    </div>
                </div>
                <p className="page-subtitle" style={{ marginBottom: '1rem' }}>
                    Interval: random between 10 and 20 minutes per run.
                </p>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    {!isRunning ? (
                        <button
                            className="btn btn-primary btn-lg"
                            onClick={startAutonomous}
                            disabled={isRunning}
                        >
                            <span>[>]</span> Start Autonomous Mode
                        </button>
                    ) : (
                        <button
                            className="btn btn-danger btn-lg"
                            onClick={stopAutonomous}
                        >
                            <span>[X]</span> Stop Autonomous Mode
                        </button>
                    )}
                    {isRunning && countdownMs != null && (
                        <span className="badge badge-info" style={{ padding: '0.5rem 1rem' }}>
                            Next attack in: {formatCountdown(countdownMs)}
                        </span>
                    )}
                </div>
            </div>

            {/* Current state */}
            {currentState && (
                <div className="card animate-fade-in" style={{ marginBottom: '2rem' }}>
                    <div className="card-header">
                        <h2 className="card-title">
                            <span>[#]</span> Current State
                        </h2>
                    </div>
                    <div className="grid-4">
                        <div className="stat-card">
                            <div
                                className="stat-value"
                                style={{ color: accessLevelColors[currentState.current_access_level] }}
                            >
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

            {/* Last run result */}
            {lastResult && (
                <div className="card animate-fade-in" style={{ marginBottom: '2rem' }}>
                    <div className="card-header">
                        <h2 className="card-title">
                            <span>[=]</span> Last Attack Run
                        </h2>
                        <span
                            className="badge"
                            style={{
                                background: `${accessLevelColors[lastResult.final_access_level]}15`,
                                color: accessLevelColors[lastResult.final_access_level]
                            }}
                        >
                            {lastResult.final_access_level.toUpperCase()}
                        </span>
                    </div>
                    <div className="grid-4" style={{ marginBottom: '1rem' }}>
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: '#00ff88' }}>
                                {lastResult.successful_attacks}
                            </div>
                            <div className="stat-label">Successful</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: '#ff4444' }}>
                                {lastResult.failed_attacks}
                            </div>
                            <div className="stat-label">Failed</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{lastResult.total_iterations}</div>
                            <div className="stat-label">Total</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{lastResult.discovered_vulnerabilities?.length ?? 0}</div>
                            <div className="stat-label">Vulns</div>
                        </div>
                    </div>
                    {lastResult.attack_path && lastResult.attack_path.length > 0 && (
                        <AttackPathVisualization
                            attackPath={lastResult.attack_path}
                            finalAccessLevel={lastResult.final_access_level}
                        />
                    )}
                </div>
            )}

            {/* Run log */}
            <div className="card animate-fade-in">
                <div className="card-header">
                    <h2 className="card-title">
                        <span>[~]</span> Run Log
                    </h2>
                </div>
                <div className="results-list" style={{ maxHeight: '320px', overflowY: 'auto' }}>
                    {runLog.length === 0 ? (
                        <p className="empty-state">No runs yet. Start autonomous mode to log attacks.</p>
                    ) : (
                        runLog.map((entry, idx) => (
                            <div key={idx} className="result-item">
                                {entry.error ? (
                                    <span style={{ color: '#ff4444' }}>[{entry.time}] Error: {entry.error}</span>
                                ) : (
                                    <span style={{ color: '#9ca3af' }}>
                                        [{entry.time}] Success: {entry.success} | Failed: {entry.failed} |
                                        Final: <strong style={{ color: accessLevelColors[entry.finalAccess] }}>{entry.finalAccess}</strong>
                                    </span>
                                )}
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    )
}

export default AutonomousSchedulerPage
