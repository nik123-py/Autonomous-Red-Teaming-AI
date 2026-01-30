import React, { useState } from 'react'
import './Dashboard.css'

function Dashboard({
  currentState,
  isSimulating,
  simulationResult,
  onStartSimulation,
  onReset,
  onExecuteAttack
}) {
  const [iterations, setIterations] = useState(100)
  const [targetHost, setTargetHost] = useState('')

  const accessLevelColors = {
    none: '#ff4444',
    public: '#ffaa00',
    internal: '#00aaff',
    admin: '#00ff88'
  }

  const handleStartSimulation = () => {
    onStartSimulation(iterations, targetHost || null)
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Control Panel</h2>
        <div className="dashboard-actions">
          <button
            className="btn btn-primary"
            onClick={handleStartSimulation}
            disabled={isSimulating}
          >
            {isSimulating ? 'Running Simulation...' : 'Start Simulation'}
          </button>
          <button className="btn btn-secondary" onClick={onReset}>
            Reset Environment
          </button>
        </div>
      </div>

      <div className="simulation-config">
        <div className="config-item">
          <label>Iterations:</label>
          <input
            type="number"
            value={iterations}
            onChange={(e) => setIterations(parseInt(e.target.value) || 100)}
            min="10"
            max="500"
          />
        </div>
        <div className="config-item">
          <label>Target Host (optional):</label>
          <input
            type="text"
            value={targetHost}
            onChange={(e) => setTargetHost(e.target.value)}
            placeholder="192.168.1.100"
          />
        </div>
      </div>

      {currentState && (
        <div className="state-panel">
          <h3>Current State</h3>
          <div className="state-grid">
            <div className="state-card">
              <div className="state-label">Access Level</div>
              <div
                className="state-value access-level"
                style={{ color: accessLevelColors[currentState.current_access_level] }}
              >
                {currentState.current_access_level.toUpperCase()}
              </div>
            </div>
            <div className="state-card">
              <div className="state-label">Iterations</div>
              <div className="state-value">{currentState.iteration_count}</div>
            </div>
            <div className="state-card">
              <div className="state-label">Visited Components</div>
              <div className="state-value">{currentState.visited_components.length}</div>
            </div>
            <div className="state-card">
              <div className="state-label">Discovered Services</div>
              <div className="state-value">{currentState.discovered_services.length}</div>
            </div>
            <div className="state-card">
              <div className="state-label">Vulnerabilities</div>
              <div className="state-value">{currentState.discovered_vulnerabilities.length}</div>
            </div>
            <div className="state-card">
              <div className="state-label">Blocked IPs</div>
              <div className="state-value">{currentState.blocked_ips.length}</div>
            </div>
            {currentState.hint_available === 1 && (
              <div className="state-card hint-card">
                <div className="state-label">Exploit-DB Hint</div>
                <div className="state-value hint-value">
                  {currentState.strategic_hint ? currentState.strategic_hint.replace(/_/g, ' ').toUpperCase() : 'Available'}
                </div>
                <div className="hint-confidence">
                  {(currentState.hint_confidence * 100).toFixed(0)}% confidence
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {simulationResult && simulationResult.strategic_hint_used && (
        <div className="hint-result-panel">
          <h3>Exploit-DB Strategic Hint</h3>
          <div className="hint-info">
            <div className="hint-item">
              <strong>Hint Used:</strong> {simulationResult.strategic_hint_used.replace(/_/g, ' ').toUpperCase()}
            </div>
            <div className={`hint-item ${simulationResult.hint_success ? 'success' : 'failed'}`}>
              <strong>Result:</strong> {simulationResult.hint_success ? '✓ Successful' : '✗ Failed'}
            </div>
          </div>
        </div>
      )}

      {simulationResult && (
        <div className="simulation-results">
          <h3>Simulation Results</h3>
          <div className="results-grid">
            <div className="result-card success">
              <div className="result-label">Successful Attacks</div>
              <div className="result-value">{simulationResult.successful_attacks}</div>
            </div>
            <div className="result-card failure">
              <div className="result-label">Failed Attacks</div>
              <div className="result-value">{simulationResult.failed_attacks}</div>
            </div>
            <div className="result-card">
              <div className="result-label">Final Access Level</div>
              <div
                className="result-value"
                style={{ color: accessLevelColors[simulationResult.final_access_level] }}
              >
                {simulationResult.final_access_level.toUpperCase()}
              </div>
            </div>
            <div className="result-card">
              <div className="result-label">Total Iterations</div>
              <div className="result-value">{simulationResult.total_iterations}</div>
            </div>
          </div>

          {simulationResult.discovered_vulnerabilities.length > 0 && (
            <div className="vulnerabilities-list">
              <h4>Discovered Vulnerabilities</h4>
              <ul>
                {simulationResult.discovered_vulnerabilities.map((vuln, idx) => (
                  <li key={idx}>{vuln}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default Dashboard

