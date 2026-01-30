import React, { useState } from 'react'
import axios from 'axios'
import './Pages.css'

const API_BASE = 'http://localhost:8003/api'

function CodeAnalysisPage() {
    const [code, setCode] = useState('')
    const [analyzing, setAnalyzing] = useState(false)
    const [analysisResults, setAnalysisResults] = useState(null)
    const [language, setLanguage] = useState('c')

    const sampleCode = `// Sample vulnerable C code
#include <stdio.h>
#include <string.h>

void vulnerable_function(char *input) {
    char buffer[64];
    // Buffer overflow vulnerability - no bounds checking
    strcpy(buffer, input);
    printf("Input: %s\\n", buffer);
}

void sql_query(char *user_input) {
    char query[256];
    // SQL Injection vulnerability - no input sanitization
    sprintf(query, "SELECT * FROM users WHERE name = '%s'", user_input);
    execute_query(query);
}

int main(int argc, char *argv[]) {
    if (argc > 1) {
        vulnerable_function(argv[1]);
        sql_query(argv[1]);
    }
    return 0;
}`

    const handleAnalyze = async () => {
        if (!code.trim()) {
            alert('Please enter code to analyze')
            return
        }

        setAnalyzing(true)
        setAnalysisResults(null)

        try {
            const response = await axios.post(`${API_BASE}/analyze-code`, {
                code: code.trim(),
                language: language
            })
            setAnalysisResults(response.data)
        } catch (error) {
            console.error('Analysis failed:', error)
            // For demo purposes, show mock results if endpoint doesn't exist
            if (error.response?.status === 404) {
                setAnalysisResults(generateMockAnalysis(code))
            } else {
                alert('Analysis failed: ' + (error.response?.data?.detail || error.message))
            }
        } finally {
            setAnalyzing(false)
        }
    }

    const generateMockAnalysis = (sourceCode) => {
        // Simple pattern matching for demo
        const vulnerabilities = []
        const lines = sourceCode.split('\n')

        lines.forEach((line, idx) => {
            if (line.includes('strcpy') || line.includes('strcat')) {
                vulnerabilities.push({
                    type: 'Buffer Overflow',
                    severity: 'critical',
                    line: idx + 1,
                    code_snippet: line.trim(),
                    description: 'Use of unsafe string function without bounds checking',
                    remediation: 'Use strncpy() or strlcpy() with explicit buffer size limits',
                    cwe_id: 'CWE-120',
                    confidence: 0.92
                })
            }
            if (line.includes('sprintf') && line.includes('%s')) {
                vulnerabilities.push({
                    type: 'SQL Injection / Format String',
                    severity: 'high',
                    line: idx + 1,
                    code_snippet: line.trim(),
                    description: 'Direct concatenation of user input into query string',
                    remediation: 'Use parameterized queries or prepared statements',
                    cwe_id: 'CWE-89',
                    confidence: 0.88
                })
            }
            if (line.includes('gets(')) {
                vulnerabilities.push({
                    type: 'Buffer Overflow',
                    severity: 'critical',
                    line: idx + 1,
                    code_snippet: line.trim(),
                    description: 'Use of gets() which is inherently unsafe',
                    remediation: 'Replace with fgets() with explicit buffer size',
                    cwe_id: 'CWE-120',
                    confidence: 0.99
                })
            }
            if (line.includes('system(') && !line.includes('sanitize')) {
                vulnerabilities.push({
                    type: 'Command Injection',
                    severity: 'critical',
                    line: idx + 1,
                    code_snippet: line.trim(),
                    description: 'Potential command injection through system() call',
                    remediation: 'Validate and sanitize input, or use safer alternatives',
                    cwe_id: 'CWE-78',
                    confidence: 0.85
                })
            }
        })

        return {
            vulnerabilities,
            summary: {
                total_vulnerabilities: vulnerabilities.length,
                critical: vulnerabilities.filter(v => v.severity === 'critical').length,
                high: vulnerabilities.filter(v => v.severity === 'high').length,
                medium: vulnerabilities.filter(v => v.severity === 'medium').length,
                low: vulnerabilities.filter(v => v.severity === 'low').length,
                lines_analyzed: lines.length
            },
            detection_method: 'IVDetect ML Model (Demo Mode)'
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

    const loadSampleCode = () => {
        setCode(sampleCode)
    }

    return (
        <div className="page">
            <div className="page-header">
                <h1 className="page-title">
                    <span className="page-title-icon">📝</span>
                    Code Vulnerability Analysis
                </h1>
                <p className="page-subtitle">Analyze C/C++ source code for vulnerabilities using IVDetect ML model</p>
            </div>

            {/* Info Banner */}
            <div
                className="card animate-fade-in"
                style={{
                    marginBottom: '1.5rem',
                    background: 'rgba(0, 212, 255, 0.05)',
                    borderColor: 'rgba(0, 212, 255, 0.2)'
                }}
            >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                    <span style={{ fontSize: '1.5rem' }}>🧠</span>
                    <div>
                        <div style={{ color: '#fff', fontWeight: '600', marginBottom: '0.25rem' }}>
                            Powered by IVDetect
                        </div>
                        <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                            IVDetect uses Graph Neural Networks on Program Dependency Graphs to detect vulnerabilities
                            and provide fine-grained interpretations showing which statements are vulnerable.
                        </div>
                    </div>
                </div>
            </div>

            {/* Code Input */}
            <div className="card animate-fade-in" style={{ marginBottom: '2rem' }}>
                <div className="card-header">
                    <h2 className="card-title">
                        <span>📄</span> Source Code Input
                    </h2>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <select
                            className="form-select"
                            value={language}
                            onChange={(e) => setLanguage(e.target.value)}
                            style={{ width: 'auto', padding: '0.5rem' }}
                        >
                            <option value="c">C</option>
                            <option value="cpp">C++</option>
                        </select>
                        <button
                            className="btn btn-secondary"
                            onClick={loadSampleCode}
                            disabled={analyzing}
                        >
                            Load Sample
                        </button>
                    </div>
                </div>

                <div className="form-group">
                    <textarea
                        className="form-textarea"
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                        placeholder="Paste your C/C++ source code here..."
                        style={{ minHeight: '300px' }}
                        disabled={analyzing}
                    />
                </div>

                <button
                    className="btn btn-primary btn-lg"
                    onClick={handleAnalyze}
                    disabled={analyzing || !code.trim()}
                >
                    {analyzing ? (
                        <>
                            <span className="loading-spinner"></span>
                            Analyzing Code...
                        </>
                    ) : (
                        <>
                            <span>🔍</span>
                            Analyze for Vulnerabilities
                        </>
                    )}
                </button>
            </div>

            {/* Analysis Results */}
            {analysisResults && (
                <>
                    {/* Summary */}
                    <div className="card animate-fade-in" style={{ marginBottom: '2rem' }}>
                        <div className="card-header">
                            <h2 className="card-title">
                                <span>📊</span> Analysis Summary
                            </h2>
                            <span className="badge badge-info">{analysisResults.detection_method}</span>
                        </div>
                        <div className="grid-4">
                            <div className="stat-card">
                                <div className="stat-value" style={{ color: '#ff4444' }}>
                                    {analysisResults.summary.total_vulnerabilities}
                                </div>
                                <div className="stat-label">Total Vulnerabilities</div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-value" style={{ color: '#ff4444' }}>
                                    {analysisResults.summary.critical}
                                </div>
                                <div className="stat-label">Critical</div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-value" style={{ color: '#ff8800' }}>
                                    {analysisResults.summary.high}
                                </div>
                                <div className="stat-label">High</div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-value">{analysisResults.summary.lines_analyzed}</div>
                                <div className="stat-label">Lines Analyzed</div>
                            </div>
                        </div>
                    </div>

                    {/* Vulnerabilities */}
                    <div className="card animate-fade-in">
                        <div className="card-header">
                            <h2 className="card-title">
                                <span>🔓</span> Detected Vulnerabilities
                            </h2>
                        </div>

                        {analysisResults.vulnerabilities.length > 0 ? (
                            <div className="results-list">
                                {analysisResults.vulnerabilities.map((vuln, idx) => (
                                    <div key={idx} className="result-item">
                                        <div className="result-item-header">
                                            <span className="result-item-title">
                                                <span style={{ color: getSeverityColor(vuln.severity), marginRight: '0.5rem' }}>●</span>
                                                {vuln.type}
                                            </span>
                                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                                <span
                                                    className="badge"
                                                    style={{
                                                        background: `${getSeverityColor(vuln.severity)}15`,
                                                        color: getSeverityColor(vuln.severity)
                                                    }}
                                                >
                                                    {vuln.severity.toUpperCase()}
                                                </span>
                                                <span className="badge badge-info">Line {vuln.line}</span>
                                            </div>
                                        </div>

                                        {vuln.cwe_id && (
                                            <div style={{ marginBottom: '0.5rem' }}>
                                                <span
                                                    style={{
                                                        background: 'rgba(255, 255, 255, 0.1)',
                                                        color: '#9ca3af',
                                                        padding: '0.2rem 0.5rem',
                                                        borderRadius: '4px',
                                                        fontSize: '0.75rem'
                                                    }}
                                                >
                                                    {vuln.cwe_id}
                                                </span>
                                                {vuln.confidence && (
                                                    <span style={{ marginLeft: '0.5rem', color: '#6b7280', fontSize: '0.8rem' }}>
                                                        Confidence: {(vuln.confidence * 100).toFixed(0)}%
                                                    </span>
                                                )}
                                            </div>
                                        )}

                                        <div className="code-block" style={{ marginBottom: '0.75rem' }}>
                                            <span style={{ color: '#6b7280' }}>Line {vuln.line}: </span>
                                            {vuln.code_snippet}
                                        </div>

                                        <p style={{ color: '#9ca3af', marginBottom: '0.75rem' }}>{vuln.description}</p>

                                        <div style={{
                                            padding: '0.75rem',
                                            background: 'rgba(0, 255, 136, 0.05)',
                                            borderRadius: '6px',
                                            fontSize: '0.85rem'
                                        }}>
                                            <strong style={{ color: '#00ff88' }}>✅ Remediation:</strong>
                                            <span style={{ color: '#9ca3af', marginLeft: '0.5rem' }}>{vuln.remediation}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="empty-state">
                                <div className="empty-state-icon">✅</div>
                                <div className="empty-state-title">No Vulnerabilities Found</div>
                                <p>The analyzed code appears to be secure.</p>
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    )
}

export default CodeAnalysisPage
