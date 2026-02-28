import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './Pages.css'

const API_BASE = 'http://localhost:8003/api'

function RLAgentPage() {
    const [agentStats, setAgentStats] = useState(null)
    const [performance, setPerformance] = useState(null)
    const [qTableSample, setQTableSample] = useState(null)
    const [loading, setLoading] = useState(true)
    const [autoRefresh, setAutoRefresh] = useState(true)
    const [refreshInterval, setRefreshInterval] = useState(2000) // 2 seconds

    useEffect(() => {
        fetchAllData()
        
        // Auto-refresh if enabled
        let interval = null
        if (autoRefresh) {
            interval = setInterval(fetchAllData, refreshInterval)
        }
        
        return () => {
            if (interval) clearInterval(interval)
        }
    }, [autoRefresh, refreshInterval])

    const fetchAllData = async () => {
        try {
            const [statsRes, perfRes, qTableRes] = await Promise.all([
                axios.get(`${API_BASE}/rl-agent/stats`),
                axios.get(`${API_BASE}/rl-agent/performance`),
                axios.get(`${API_BASE}/rl-agent/q-table`)
            ])
            
            setAgentStats(statsRes.data)
            setPerformance(perfRes.data)
            setQTableSample(qTableRes.data)
            setLoading(false)
        } catch (error) {
            console.error('Failed to fetch RL agent data:', error)
            setLoading(false)
        }
    }

    const resetAgent = async () => {
        if (!window.confirm('Are you sure you want to reset the RL agent? This will clear all learned Q-values.')) {
            return
        }
        try {
            await axios.post(`${API_BASE}/rl-agent/reset`)
            await fetchAllData()
            alert('RL agent reset successfully!')
        } catch (error) {
            console.error('Failed to reset agent:', error)
            alert('Failed to reset agent: ' + (error.response?.data?.detail || error.message))
        }
    }

    const saveModel = async () => {
        try {
            await axios.post(`${API_BASE}/rl-agent/save`)
            alert('RL model saved successfully!')
        } catch (error) {
            console.error('Failed to save model:', error)
            alert('Failed to save model: ' + (error.response?.data?.detail || error.message))
        }
    }

    const loadModel = async () => {
        if (!window.confirm('Load saved RL model? This will replace current Q-table.')) {
            return
        }
        try {
            await axios.post(`${API_BASE}/rl-agent/load`)
            await fetchAllData()
            alert('RL model loaded successfully!')
        } catch (error) {
            console.error('Failed to load model:', error)
            alert('Failed to load model: ' + (error.response?.data?.detail || error.message))
        }
    }

    // Format percentage
    const formatPercent = (value) => {
        return (value * 100).toFixed(1) + '%'
    }

    // Format large numbers
    const formatNumber = (value) => {
        if (value >= 1000000) return (value / 1000000).toFixed(2) + 'M'
        if (value >= 1000) return (value / 1000).toFixed(1) + 'K'
        return value.toString()
    }

    if (loading && !agentStats) {
        return (
            <div className="page">
                <div className="page-header">
                    <h1 className="page-title">
                        <span className="page-title-icon">🧠</span>
                        RL Agent Performance
                    </h1>
                </div>
                <div className="card animate-fade-in" style={{ textAlign: 'center', padding: '3rem' }}>
                    <span className="loading-spinner" style={{ marginRight: '1rem' }} />
                    <span>Loading RL agent statistics...</span>
                </div>
            </div>
        )
    }

    return (
        <div className="page">
            <div className="page-header">
                <h1 className="page-title">
                    <span className="page-title-icon">🧠</span>
                    RL Agent Performance Dashboard
                </h1>
                <p className="page-subtitle">
                    Monitor reinforcement learning agent statistics, learning progress, and performance metrics
                </p>
            </div>

            {/* Control Panel */}
            <div className="card animate-fade-in" style={{ marginBottom: '1.5rem' }}>
                <div className="card-header">
                    <h2 className="card-title">
                        <span>[⚙️]</span> Controls
                    </h2>
                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                        <label style={{ fontSize: '0.85rem', color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <input
                                type="checkbox"
                                checked={autoRefresh}
                                onChange={(e) => setAutoRefresh(e.target.checked)}
                                style={{ marginRight: '0.25rem' }}
                            />
                            Auto-refresh
                        </label>
                        {autoRefresh && (
                            <select
                                className="form-input"
                                value={refreshInterval}
                                onChange={(e) => setRefreshInterval(parseInt(e.target.value))}
                                style={{ width: '120px', fontSize: '0.8rem', padding: '0.3rem 0.5rem' }}
                            >
                                <option value={1000}>1 sec</option>
                                <option value={2000}>2 sec</option>
                                <option value={5000}>5 sec</option>
                                <option value={10000}>10 sec</option>
                            </select>
                        )}
                        <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={fetchAllData}
                            style={{ fontSize: '0.8rem', padding: '0.3rem 0.6rem' }}
                        >
                            🔄 Refresh
                        </button>
                    </div>
                </div>
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <button className="btn btn-secondary" onClick={saveModel}>
                        💾 Save Model
                    </button>
                    <button className="btn btn-secondary" onClick={loadModel}>
                        📂 Load Model
                    </button>
                    <button className="btn btn-danger" onClick={resetAgent}>
                        🔄 Reset Agent
                    </button>
                </div>
            </div>

            {/* Agent Type & Features */}
            {agentStats && (
                <div className="card animate-fade-in" style={{ marginBottom: '1.5rem' }}>
                    <div className="card-header">
                        <h2 className="card-title">
                            <span>[🤖]</span> Agent Configuration
                        </h2>
                    </div>
                    <div style={{ marginBottom: '1rem' }}>
                        <p style={{ color: '#9ca3af', marginBottom: '0.5rem' }}>
                            <strong style={{ color: '#fff' }}>Type:</strong> {agentStats.agent_type}
                        </p>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                            {agentStats.features.map((feature, idx) => (
                                <span
                                    key={idx}
                                    className="badge badge-info"
                                    style={{ fontSize: '0.75rem', padding: '0.25rem 0.75rem' }}
                                >
                                    {feature}
                                </span>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Current Metrics */}
            {agentStats && (
                <div className="card animate-fade-in" style={{ marginBottom: '1.5rem' }}>
                    <div className="card-header">
                        <h2 className="card-title">
                            <span>[📊]</span> Current Metrics
                        </h2>
                    </div>
                    <div className="grid-4">
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: '#00d4ff' }}>
                                {agentStats.epsilon.toFixed(3)}
                            </div>
                            <div className="stat-label">Epsilon (Exploration)</div>
                            <div style={{ fontSize: '0.7rem', color: '#6b7280', marginTop: '0.25rem' }}>
                                {formatPercent(agentStats.epsilon)} exploration rate
                            </div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: '#00ff88' }}>
                                {agentStats.learning_rate.toFixed(3)}
                            </div>
                            <div className="stat-label">Learning Rate</div>
                            <div style={{ fontSize: '0.7rem', color: '#6b7280', marginTop: '0.25rem' }}>
                                Adaptive: {agentStats.learning_rate > 0.1 ? 'High' : 'Low'}
                            </div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: '#ffaa00' }}>
                                {agentStats.temperature.toFixed(2)}
                            </div>
                            <div className="stat-label">Temperature</div>
                            <div style={{ fontSize: '0.7rem', color: '#6b7280', marginTop: '0.25rem' }}>
                                Boltzmann exploration
                            </div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: agentStats.success_rate > 0.5 ? '#00ff88' : '#ffaa00' }}>
                                {formatPercent(agentStats.success_rate)}
                            </div>
                            <div className="stat-label">Success Rate</div>
                            <div style={{ fontSize: '0.7rem', color: '#6b7280', marginTop: '0.25rem' }}>
                                {agentStats.success_count} / {agentStats.success_count + agentStats.failure_count}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Learning Statistics */}
            {agentStats && (
                <div className="card animate-fade-in" style={{ marginBottom: '1.5rem' }}>
                    <div className="card-header">
                        <h2 className="card-title">
                            <span>[📈]</span> Learning Statistics
                        </h2>
                    </div>
                    <div className="grid-4">
                        <div className="stat-card">
                            <div className="stat-value">{agentStats.episode_count}</div>
                            <div className="stat-label">Episodes</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{formatNumber(agentStats.step_count)}</div>
                            <div className="stat-label">Total Steps</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: '#00d4ff' }}>
                                {formatNumber(agentStats.q_table_size)}
                            </div>
                            <div className="stat-label">Q-Table Entries</div>
                            <div style={{ fontSize: '0.7rem', color: '#6b7280', marginTop: '0.25rem' }}>
                                State-action pairs
                            </div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: '#00ff88' }}>
                                {formatNumber(agentStats.replay_buffer_size)}
                            </div>
                            <div className="stat-label">Replay Buffer</div>
                            <div style={{ fontSize: '0.7rem', color: '#6b7280', marginTop: '0.25rem' }}>
                                Stored experiences
                            </div>
                        </div>
                    </div>
                    <div style={{ marginTop: '1.5rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                        <div>
                            <div style={{ color: '#9ca3af', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                                Total Rewards
                            </div>
                            <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: agentStats.total_rewards >= 0 ? '#00ff88' : '#ff4444' }}>
                                {agentStats.total_rewards.toFixed(2)}
                            </div>
                        </div>
                        <div>
                            <div style={{ color: '#9ca3af', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                                Average Reward
                            </div>
                            <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: agentStats.average_reward >= 0 ? '#00ff88' : '#ff4444' }}>
                                {agentStats.average_reward.toFixed(2)}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Performance Trends */}
            {performance && performance.learning_progress && (
                <div className="card animate-fade-in" style={{ marginBottom: '1.5rem' }}>
                    <div className="card-header">
                        <h2 className="card-title">
                            <span>[📉]</span> Learning Curves
                        </h2>
                    </div>
                    
                    {performance.learning_progress.episodes.length > 0 ? (
                        <div>
                            {/* Rewards Over Episodes */}
                            <div style={{ marginBottom: '2rem' }}>
                                <h3 style={{ color: '#fff', marginBottom: '1rem', fontSize: '1rem' }}>
                                    Rewards Over Episodes
                                </h3>
                                <div style={{ 
                                    background: 'rgba(0, 0, 0, 0.3)', 
                                    borderRadius: '8px', 
                                    padding: '1rem',
                                    minHeight: '200px',
                                    position: 'relative'
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '2px', height: '180px' }}>
                                        {performance.learning_progress.rewards.map((reward, idx) => {
                                            const maxReward = Math.max(...performance.learning_progress.rewards, 1)
                                            const height = Math.abs((reward / maxReward) * 100)
                                            const isPositive = reward >= 0
                                            return (
                                                <div
                                                    key={idx}
                                                    style={{
                                                        flex: 1,
                                                        background: isPositive ? 'rgba(0, 255, 136, 0.6)' : 'rgba(255, 68, 68, 0.6)',
                                                        height: `${Math.min(height, 100)}%`,
                                                        borderRadius: '2px 2px 0 0',
                                                        minHeight: '2px',
                                                        transition: 'all 0.3s ease'
                                                    }}
                                                    title={`Episode ${performance.learning_progress.episodes[idx]}: ${reward.toFixed(2)}`}
                                                />
                                            )
                                        })}
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem', fontSize: '0.75rem', color: '#6b7280' }}>
                                        <span>Episode {performance.learning_progress.episodes[0] || 0}</span>
                                        <span>Episode {performance.learning_progress.episodes[performance.learning_progress.episodes.length - 1] || 0}</span>
                                    </div>
                                </div>
                            </div>

                            {/* Success Rate Trend */}
                            <div>
                                <h3 style={{ color: '#fff', marginBottom: '1rem', fontSize: '1rem' }}>
                                    Success Rate Trend
                                </h3>
                                <div style={{ 
                                    background: 'rgba(0, 0, 0, 0.3)', 
                                    borderRadius: '8px', 
                                    padding: '1rem',
                                    minHeight: '200px',
                                    position: 'relative'
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '2px', height: '180px' }}>
                                        {performance.learning_progress.success_rates.map((rate, idx) => {
                                            const height = rate * 100
                                            return (
                                                <div
                                                    key={idx}
                                                    style={{
                                                        flex: 1,
                                                        background: `linear-gradient(to top, 
                                                            ${rate > 0.7 ? 'rgba(0, 255, 136, 0.8)' : rate > 0.4 ? 'rgba(255, 170, 0, 0.8)' : 'rgba(255, 68, 68, 0.8)'}, 
                                                            ${rate > 0.7 ? 'rgba(0, 255, 136, 0.4)' : rate > 0.4 ? 'rgba(255, 170, 0, 0.4)' : 'rgba(255, 68, 68, 0.4)'})`,
                                                        height: `${height}%`,
                                                        borderRadius: '2px 2px 0 0',
                                                        minHeight: '2px',
                                                        transition: 'all 0.3s ease'
                                                    }}
                                                    title={`Episode ${performance.learning_progress.episodes[idx]}: ${formatPercent(rate)}`}
                                                />
                                            )
                                        })}
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem', fontSize: '0.75rem', color: '#6b7280' }}>
                                        <span>0%</span>
                                        <span>100%</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                            <p>No learning data yet. Run simulations to see learning curves.</p>
                        </div>
                    )}
                </div>
            )}

            {/* Q-Table Sample */}
            {qTableSample && (
                <div className="card animate-fade-in" style={{ marginBottom: '1.5rem' }}>
                    <div className="card-header">
                        <h2 className="card-title">
                            <span>[🗂️]</span> Q-Table Sample
                        </h2>
                    </div>
                    <div style={{ marginBottom: '0.75rem', color: '#9ca3af', fontSize: '0.85rem' }}>
                        Total States: <strong style={{ color: '#fff' }}>{qTableSample.total_states}</strong>
                        {qTableSample.note && <div style={{ marginTop: '0.25rem', fontSize: '0.75rem' }}>{qTableSample.note}</div>}
                    </div>
                    {Object.keys(qTableSample.sample).length > 0 ? (
                        <div style={{ 
                            background: 'rgba(0, 0, 0, 0.3)', 
                            borderRadius: '8px', 
                            padding: '1rem',
                            maxHeight: '400px',
                            overflowY: 'auto'
                        }}>
                            {Object.entries(qTableSample.sample).map(([state, actions]) => (
                                <div key={state} style={{ marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
                                    <div style={{ color: '#00d4ff', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                                        State: <span style={{ color: '#fff' }}>{state}</span>
                                    </div>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.5rem' }}>
                                        {Object.entries(actions).map(([action, qValue]) => (
                                            <div
                                                key={action}
                                                style={{
                                                    background: qValue > 0 ? 'rgba(0, 255, 136, 0.1)' : 'rgba(255, 68, 68, 0.1)',
                                                    border: `1px solid ${qValue > 0 ? 'rgba(0, 255, 136, 0.3)' : 'rgba(255, 68, 68, 0.3)'}`,
                                                    borderRadius: '4px',
                                                    padding: '0.5rem',
                                                    fontSize: '0.8rem'
                                                }}
                                            >
                                                <div style={{ color: '#9ca3af', fontSize: '0.7rem', marginBottom: '0.25rem' }}>
                                                    {action.replace(/_/g, ' ')}
                                                </div>
                                                <div style={{ 
                                                    color: qValue > 0 ? '#00ff88' : '#ff4444',
                                                    fontWeight: 'bold',
                                                    fontSize: '0.9rem'
                                                }}>
                                                    Q: {qValue.toFixed(2)}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                            <p>Q-table is empty. The agent hasn't learned any state-action values yet.</p>
                            <p style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>Run simulations to start learning!</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

export default RLAgentPage
