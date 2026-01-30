import React, { useState } from 'react'
import axios from 'axios'
import './ScanPanel.css'

const API_BASE = 'http://localhost:8003/api'

function ScanPanel() {
  const [target, setTarget] = useState('')
  const [scanType, setScanType] = useState('full')
  const [scanning, setScanning] = useState(false)
  const [scanResults, setScanResults] = useState(null)
  const [mlModelStatus, setMlModelStatus] = useState(null)

  // Check ML model status on component mount
  React.useEffect(() => {
    const checkModelStatus = async () => {
      try {
        // Try to get model status from backend
        const response = await axios.get(`${API_BASE}/model-status`)
        setMlModelStatus(response.data)
      } catch (error) {
        // Model status endpoint might not exist, that's okay
        setMlModelStatus({ available: false })
      }
    }
    checkModelStatus()
  }, [])

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
        scan_type: scanType
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
    <div className="scan-panel">
      <h3>Network & Vulnerability Scanner</h3>
      
      {mlModelStatus && (
        <div className={`ml-status-indicator ${mlModelStatus.available ? 'available' : 'unavailable'}`}>
          {mlModelStatus.available ? (
            <>
              <span className="ml-status-icon">🤖</span>
              <span>ML Model: <strong>Active</strong></span>
            </>
          ) : (
            <>
              <span className="ml-status-icon">⚠️</span>
              <span>ML Model: <strong>Unavailable</strong> (using rule-based detection)</span>
            </>
          )}
        </div>
      )}

      <div className="scan-config">
        <div className="scan-input-group">
          <label>Target:</label>
          <input
            type="text"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="192.168.1.100 or example.com"
            disabled={scanning}
          />
        </div>

        <div className="scan-input-group">
          <label>Scan Type:</label>
          <select
            value={scanType}
            onChange={(e) => setScanType(e.target.value)}
            disabled={scanning}
          >
            <option value="full">Full Scan</option>
            <option value="ports">Port Scan Only</option>
            <option value="vuln">Vulnerability Scan Only</option>
          </select>
        </div>

        <button
          className="btn btn-primary"
          onClick={handleScan}
          disabled={scanning || !target.trim()}
        >
          {scanning ? 'Scanning...' : 'Start Scan'}
        </button>
      </div>

      {scanResults && (
        <div className="scan-results">
          <div className="result-section">
            <h4>Target: {scanResults.target}</h4>
            <div className="result-stats">
              <span>Open Ports: {scanResults.open_ports.length}</span>
              <span>Services: {scanResults.services.length}</span>
              <span>Vulnerabilities: {scanResults.vulnerabilities.length}</span>
              {scanResults.vulnerabilities.some(v => v.detection_method === 'ML Model') && (
                <span className="ml-model-badge" title="ML Model Detections">
                  🤖 ML Model: {scanResults.vulnerabilities.filter(v => v.detection_method === 'ML Model').length}
                </span>
              )}
              {scanResults.generated_exploits && scanResults.generated_exploits.length > 0 && (
                <span className="exploit-count">
                  <strong>Generated Exploits: {scanResults.generated_exploits.length}</strong>
                </span>
              )}
            </div>
          </div>

          {scanResults.open_ports.length > 0 && (
            <div className="result-section">
              <h4>Open Ports</h4>
              <div className="ports-list">
                {scanResults.open_ports.map((port, idx) => (
                  <div key={idx} className="port-item">
                    <span className="port-number">{port.port}</span>
                    <span className="port-service">{port.service}</span>
                    {port.version && (
                      <span className="port-version">{port.version}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {scanResults.services.length > 0 && (
            <div className="result-section">
              <h4>Discovered Services</h4>
              <div className="services-list">
                {scanResults.services.map((service, idx) => (
                  <div key={idx} className="service-item">
                    <div className="service-name">{service.name}</div>
                    <div className="service-details">
                      Port {service.port} / {service.protocol}
                      {service.version && ` - ${service.version}`}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {scanResults.vulnerabilities.length > 0 && (
            <div className="result-section">
              <h4>Vulnerabilities</h4>
              <div className="vulnerabilities-list">
                {scanResults.vulnerabilities.map((vuln, idx) => (
                  <div
                    key={idx}
                    className={`vuln-item severity-${vuln.severity}`}
                  >
                    <div className="vuln-header">
                      <span className="vuln-name">{vuln.name}</span>
                      <span className={`vuln-severity ${vuln.severity}`}>
                        {vuln.severity.toUpperCase()}
                      </span>
                      {vuln.detection_method === 'ML Model' && (
                        <span className="ml-detection-badge" title="Detected by ML Model">
                          🤖 ML
                        </span>
                      )}
                      {vuln.confidence && (
                        <span className="confidence-badge" title="ML Model Confidence">
                          {Math.round(vuln.confidence * 100)}%
                        </span>
                      )}
                    </div>
                    {vuln.cve_id && (
                      <div className="vuln-cve">CVE: {vuln.cve_id}</div>
                    )}
                    {vuln.detection_method && (
                      <div className="vuln-detection-method">
                        Detection: <strong>{vuln.detection_method}</strong>
                      </div>
                    )}
                    <div className="vuln-description">{vuln.description}</div>
                    <div className="vuln-service">
                      Service: {vuln.affected_service}
                      {vuln.affected_port && `:${vuln.affected_port}`}
                    </div>
                    {vuln.exploit_available && (
                      <div className="vuln-exploit">Exploit Available</div>
                    )}
                    <div className="vuln-remediation">
                      <strong>Remediation:</strong> {vuln.remediation}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {scanResults.generated_exploits && scanResults.generated_exploits.length > 0 && (
            <div className="result-section">
              <h4>Generated Exploits</h4>
              <div className="exploits-list">
                {scanResults.generated_exploits.map((exploit, idx) => (
                  <div key={idx} className={`exploit-item impact-${exploit.impact}`}>
                    <div className="exploit-header">
                      <span className="exploit-type">{exploit.exploit_type.replace(/_/g, ' ').toUpperCase()}</span>
                      <span className={`exploit-impact ${exploit.impact}`}>
                        {exploit.impact.toUpperCase()}
                      </span>
                      <span className="exploit-probability">
                        {(exploit.success_probability * 100).toFixed(0)}% success
                      </span>
                    </div>
                    <div className="exploit-description">{exploit.description}</div>
                    <div className="exploit-payload">
                      <strong>Payload:</strong>
                      <code>{exploit.payload}</code>
                    </div>
                    <div className="exploit-target">
                      <strong>Target:</strong> {exploit.target_endpoint}
                      {exploit.target_parameter && (
                        <span> (Parameter: {exploit.target_parameter})</span>
                      )}
                    </div>
                    <div className="exploit-analysis">
                      <div className="analysis-item">
                        <strong>System Weakness:</strong>
                        <p>{exploit.system_weakness}</p>
                      </div>
                      <div className="analysis-item">
                        <strong>Vulnerability Analysis:</strong>
                        <p>{exploit.vulnerability_analysis}</p>
                      </div>
                      <div className="analysis-item">
                        <strong>Detection Method:</strong>
                        <p>{exploit.detection_method}</p>
                      </div>
                      <div className="analysis-item">
                        <strong>Remediation:</strong>
                        <p>{exploit.remediation}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {scanResults.open_ports.length === 0 &&
            scanResults.vulnerabilities.length === 0 && (
              <div className="no-results">No open ports or vulnerabilities found</div>
            )}
        </div>
      )}
    </div>
  )
}

export default ScanPanel

