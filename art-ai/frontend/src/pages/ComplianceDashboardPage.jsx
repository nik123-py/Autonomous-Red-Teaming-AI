/**
 * Compliance Dashboard Page
 * Maps security findings to compliance frameworks (PCI-DSS, HIPAA, SOC2, ISO27001)
 * Provides gap analysis and compliance scoring
 */

import React, { useState, useEffect } from 'react';
import { 
    ShieldIcon, 
    ChartIcon, 
    AlertIcon, 
    CheckIcon 
} from '../components/Icons';

const API_BASE = 'http://localhost:8003';

// Framework icons/colors
const FRAMEWORK_CONFIG = {
    'PCI-DSS': { color: '#ef4444', icon: '💳', name: 'PCI-DSS' },
    'HIPAA': { color: '#22c55e', icon: '🏥', name: 'HIPAA' },
    'SOC2': { color: '#ff8800', icon: '🔒', name: 'SOC2' },
    'ISO27001': { color: '#ff4488', icon: '🌐', name: 'ISO27001' }
};

// Severity colors
const SEVERITY_COLORS = {
    'Critical': '#ff4444',
    'High': '#ff8800',
    'Medium': '#ffaa00',
    'Low': '#22c55e'
};

export default function ComplianceDashboardPage() {
    // State management
    const [frameworks, setFrameworks] = useState([]);
    const [selectedFrameworks, setSelectedFrameworks] = useState(['PCI-DSS', 'HIPAA', 'SOC2', 'ISO27001']);
    const [vulnerabilities, setVulnerabilities] = useState([]);
    const [complianceResults, setComplianceResults] = useState(null);
    const [gapAnalysis, setGapAnalysis] = useState(null);
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('overview');
    const [error, setError] = useState(null);

    // Fetch available frameworks on mount
    useEffect(() => {
        fetchFrameworks();
        // Load vulnerabilities from latest simulation
        loadLatestVulnerabilities();
    }, []);

    // Fetch supported compliance frameworks
    const fetchFrameworks = async () => {
        try {
            const response = await fetch(`${API_BASE}/api/compliance/frameworks`);
            const data = await response.json();
            setFrameworks(data.frameworks || []);
        } catch (err) {
            console.error('Failed to fetch frameworks:', err);
        }
    };

    // Load vulnerabilities from the latest simulation
    const loadLatestVulnerabilities = async () => {
        try {
            // Get all paths and find the one with the most vulnerabilities
            const response = await fetch(`${API_BASE}/api/attack-paths`);
            if (response.ok) {
                const data = await response.json();
                const paths = data.paths || [];
                
                if (paths.length === 0) {
                    setVulnerabilities([]);
                    return;
                }
                
                // Find path with most vulnerabilities (prefer recent if tied)
                const pathWithMostVulns = paths.reduce((best, current) => {
                    const bestVulns = best.vulnerabilities?.length || 0;
                    const currentVulns = current.vulnerabilities?.length || 0;
                    return currentVulns > bestVulns ? current : best;
                }, paths[0]);
                
                setVulnerabilities(pathWithMostVulns.vulnerabilities || []);
            }
        } catch (err) {
            console.error('Failed to load vulnerabilities:', err);
        }
    };

    // Analyze compliance
    const analyzeCompliance = async () => {
        if (vulnerabilities.length === 0) {
            setError('No vulnerabilities to analyze. Run a simulation first.');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            // Fetch compliance analysis
            const complianceResponse = await fetch(`${API_BASE}/api/compliance/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    vulnerabilities,
                    frameworks: selectedFrameworks
                })
            });
            const complianceData = await complianceResponse.json();
            setComplianceResults(complianceData);

            // Fetch gap analysis
            const gapResponse = await fetch(`${API_BASE}/api/compliance/gap-analysis`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    vulnerabilities,
                    frameworks: selectedFrameworks
                })
            });
            const gapData = await gapResponse.json();
            setGapAnalysis(gapData);

        } catch (err) {
            setError(`Analysis failed: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    // Toggle framework selection
    const toggleFramework = (frameworkId) => {
        setSelectedFrameworks(prev => {
            if (prev.includes(frameworkId)) {
                return prev.filter(f => f !== frameworkId);
            }
            return [...prev, frameworkId];
        });
    };

    // Render compliance score gauge
    const renderScoreGauge = (score, framework) => {
        const config = FRAMEWORK_CONFIG[framework] || { color: '#ef4444', icon: '📋' };
        const circumference = 2 * Math.PI * 45;
        const offset = circumference - (score / 100) * circumference;

        return (
            <div className="score-gauge" style={{ textAlign: 'center' }}>
                <svg width="120" height="120" viewBox="0 0 120 120">
                    {/* Background circle */}
                    <circle
                        cx="60"
                        cy="60"
                        r="45"
                        fill="none"
                        stroke="rgba(255,255,255,0.1)"
                        strokeWidth="8"
                    />
                    {/* Score circle */}
                    <circle
                        cx="60"
                        cy="60"
                        r="45"
                        fill="none"
                        stroke={config.color}
                        strokeWidth="8"
                        strokeLinecap="round"
                        strokeDasharray={circumference}
                        strokeDashoffset={offset}
                        transform="rotate(-90 60 60)"
                        style={{ transition: 'stroke-dashoffset 0.5s ease' }}
                    />
                    {/* Score text */}
                    <text
                        x="60"
                        y="55"
                        textAnchor="middle"
                        fill={config.color}
                        fontSize="24"
                        fontWeight="bold"
                    >
                        {score.toFixed(0)}%
                    </text>
                    <text
                        x="60"
                        y="75"
                        textAnchor="middle"
                        fill="#9ca3af"
                        fontSize="10"
                    >
                        COMPLIANT
                    </text>
                </svg>
            </div>
        );
    };

    return (
        <div className="page">
            {/* Header */}
            <div className="page-header">
                <h1 className="page-title">
                    <span className="page-title-icon">
                        <ShieldIcon size={28} color="#ef4444" />
                    </span>
                    Compliance Dashboard
                </h1>
                <p className="page-subtitle">
                    Map security findings to compliance frameworks - PCI-DSS, HIPAA, SOC2, ISO27001
                </p>
            </div>

            {/* Framework Selection */}
            <div className="card" style={{ marginBottom: '1.5rem' }}>
                <div className="card-header">
                    <h3 className="card-title">Select Compliance Frameworks</h3>
                    <button
                        className="btn btn-primary"
                        onClick={analyzeCompliance}
                        disabled={loading || selectedFrameworks.length === 0}
                    >
                        {loading ? (
                            <>
                                <span className="loading-spinner" />
                                Analyzing...
                            </>
                        ) : (
                            <>Analyze Compliance</>
                        )}
                    </button>
                </div>

                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                    {Object.entries(FRAMEWORK_CONFIG).map(([id, config]) => (
                        <div
                            key={id}
                            onClick={() => toggleFramework(id)}
                            style={{
                                padding: '1rem 1.5rem',
                                background: selectedFrameworks.includes(id)
                                    ? `${config.color}20`
                                    : 'rgba(0,0,0,0.2)',
                                border: `2px solid ${selectedFrameworks.includes(id) ? config.color : 'rgba(255,255,255,0.1)'}`,
                                borderRadius: '12px',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.75rem'
                            }}
                        >
                            <span style={{ fontSize: '1.5rem' }}>{config.icon}</span>
                            <span style={{ color: selectedFrameworks.includes(id) ? config.color : '#9ca3af', fontWeight: 600 }}>
                                {config.name}
                            </span>
                        </div>
                    ))}
                </div>

                {/* Current vulnerabilities */}
                <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
                    <div style={{ color: '#9ca3af', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                        Vulnerabilities to Analyze ({vulnerabilities.length})
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                        {vulnerabilities.length > 0 ? (
                            vulnerabilities.map((vuln, idx) => (
                                <span
                                    key={idx}
                                    style={{
                                        padding: '0.25rem 0.75rem',
                                        background: 'rgba(255,68,68,0.15)',
                                        color: '#ff4444',
                                        borderRadius: '20px',
                                        fontSize: '0.8rem'
                                    }}
                                >
                                    {vuln}
                                </span>
                            ))
                        ) : (
                            <span style={{ color: '#6b7280' }}>No vulnerabilities found. Run a simulation first.</span>
                        )}
                    </div>
                </div>
            </div>

            {/* Error display */}
            {error && (
                <div style={{
                    padding: '1rem',
                    background: 'rgba(255,68,68,0.1)',
                    border: '1px solid rgba(255,68,68,0.3)',
                    borderRadius: '8px',
                    color: '#ff4444',
                    marginBottom: '1.5rem'
                }}>
                    {error}
                </div>
            )}

            {/* Results */}
            {complianceResults && (
                <>
                    {/* Tab Navigation */}
                    <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
                        {['overview', 'findings', 'roadmap'].map(tab => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab)}
                                className={`btn ${activeTab === tab ? 'btn-primary' : 'btn-secondary'}`}
                            >
                                {tab.charAt(0).toUpperCase() + tab.slice(1)}
                            </button>
                        ))}
                    </div>

                    {/* Overview Tab */}
                    {activeTab === 'overview' && (
                        <>
                            {/* Summary Stats */}
                            <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
                                <div className="stat-card">
                                    <div className="stat-value" style={{ color: '#ef4444' }}>
                                        {complianceResults.summary?.average_score?.toFixed(1) || 0}%
                                    </div>
                                    <div className="stat-label">Average Compliance</div>
                                </div>
                                <div className="stat-card">
                                    <div className="stat-value" style={{ color: '#ff4444' }}>
                                        {gapAnalysis?.summary?.critical_gaps || 0}
                                    </div>
                                    <div className="stat-label">Critical Gaps</div>
                                </div>
                                <div className="stat-card">
                                    <div className="stat-value" style={{ color: '#ff8800' }}>
                                        {gapAnalysis?.summary?.high_gaps || 0}
                                    </div>
                                    <div className="stat-label">High Gaps</div>
                                </div>
                                <div className="stat-card">
                                    <div className="stat-value" style={{ color: '#22c55e' }}>
                                        {complianceResults.summary?.frameworks_analyzed || 0}
                                    </div>
                                    <div className="stat-label">Frameworks Analyzed</div>
                                </div>
                            </div>

                            {/* Framework Scores */}
                            <div className="grid-4">
                                {complianceResults.scores?.map((score, idx) => {
                                    const config = FRAMEWORK_CONFIG[score.framework] || { color: '#ef4444', icon: '📋' };
                                    return (
                                        <div key={idx} className="card" style={{ padding: '1.5rem' }}>
                                            <div style={{ 
                                                display: 'flex', 
                                                alignItems: 'center', 
                                                gap: '0.5rem', 
                                                marginBottom: '1rem',
                                                justifyContent: 'center'
                                            }}>
                                                <span style={{ fontSize: '1.5rem' }}>{config.icon}</span>
                                                <span style={{ fontWeight: 600, color: config.color }}>
                                                    {score.framework}
                                                </span>
                                            </div>
                                            
                                            {renderScoreGauge(score.score, score.framework)}
                                            
                                            <div style={{ 
                                                display: 'grid', 
                                                gridTemplateColumns: '1fr 1fr', 
                                                gap: '0.5rem',
                                                marginTop: '1rem',
                                                fontSize: '0.8rem',
                                                color: '#9ca3af'
                                            }}>
                                                <div>Compliant: <span style={{ color: '#22c55e' }}>{score.compliant}</span></div>
                                                <div>Non-Compliant: <span style={{ color: '#ff4444' }}>{score.non_compliant}</span></div>
                                                <div>Critical: <span style={{ color: '#ff4444' }}>{score.critical_findings}</span></div>
                                                <div>High: <span style={{ color: '#ff8800' }}>{score.high_findings}</span></div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </>
                    )}

                    {/* Findings Tab */}
                    {activeTab === 'findings' && (
                        <div className="card">
                            <h3 className="card-title" style={{ marginBottom: '1.5rem' }}>
                                <AlertIcon size={20} color="#ff4444" /> Compliance Findings
                            </h3>
                            
                            <div className="results-list">
                                {Object.entries(complianceResults.findings || {}).map(([framework, findings]) => (
                                    findings.length > 0 && (
                                        <div key={framework} style={{ marginBottom: '1.5rem' }}>
                                            <div style={{ 
                                                display: 'flex', 
                                                alignItems: 'center', 
                                                gap: '0.5rem',
                                                marginBottom: '1rem',
                                                paddingBottom: '0.5rem',
                                                borderBottom: '1px solid rgba(255,255,255,0.1)'
                                            }}>
                                                <span style={{ fontSize: '1.25rem' }}>
                                                    {FRAMEWORK_CONFIG[framework]?.icon || '📋'}
                                                </span>
                                                <span style={{ 
                                                    fontWeight: 600, 
                                                    color: FRAMEWORK_CONFIG[framework]?.color || '#ef4444' 
                                                }}>
                                                    {framework}
                                                </span>
                                                <span className="badge badge-danger" style={{ marginLeft: 'auto' }}>
                                                    {findings.length} findings
                                                </span>
                                            </div>
                                            
                                            {findings.map((finding, idx) => (
                                                <div key={idx} className="result-item" style={{ marginBottom: '0.75rem' }}>
                                                    <div className="result-item-header">
                                                        <span className="result-item-title">
                                                            {finding.requirement_id}: {finding.requirement_name}
                                                        </span>
                                                        <span 
                                                            className="badge"
                                                            style={{ 
                                                                background: `${SEVERITY_COLORS[finding.severity]}20`,
                                                                color: SEVERITY_COLORS[finding.severity]
                                                            }}
                                                        >
                                                            {finding.severity}
                                                        </span>
                                                    </div>
                                                    <div style={{ fontSize: '0.85rem', color: '#9ca3af', marginBottom: '0.5rem' }}>
                                                        <strong style={{ color: '#ff4444' }}>Vulnerability:</strong> {finding.vulnerability}
                                                    </div>
                                                    <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: '0.5rem' }}>
                                                        {finding.description}
                                                    </div>
                                                    <div style={{ 
                                                        fontSize: '0.8rem', 
                                                        padding: '0.5rem',
                                                        background: 'rgba(0,255,136,0.05)',
                                                        borderRadius: '4px',
                                                        color: '#22c55e'
                                                    }}>
                                                        <strong>Remediation:</strong> {finding.remediation}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Roadmap Tab */}
                    {activeTab === 'roadmap' && gapAnalysis && (
                        <div className="card">
                            <h3 className="card-title" style={{ marginBottom: '1.5rem' }}>
                                <ChartIcon size={20} color="#ef4444" /> Remediation Roadmap
                            </h3>
                            
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                                {gapAnalysis.roadmap?.map((phase, idx) => (
                                    <div 
                                        key={idx}
                                        style={{
                                            padding: '1.5rem',
                                            background: 'rgba(0,0,0,0.2)',
                                            borderRadius: '12px',
                                            borderLeft: `4px solid ${SEVERITY_COLORS[phase.priority] || '#ef4444'}`
                                        }}
                                    >
                                        <div style={{ 
                                            display: 'flex', 
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                            marginBottom: '1rem'
                                        }}>
                                            <div>
                                                <div style={{ 
                                                    fontSize: '1.1rem', 
                                                    fontWeight: 600, 
                                                    color: '#fff',
                                                    marginBottom: '0.25rem'
                                                }}>
                                                    Phase {phase.phase}: {phase.name}
                                                </div>
                                                <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>
                                                    Timeline: {phase.timeline} | Effort: {phase.effort}
                                                </div>
                                            </div>
                                            <span 
                                                className="badge"
                                                style={{ 
                                                    background: `${SEVERITY_COLORS[phase.priority]}20`,
                                                    color: SEVERITY_COLORS[phase.priority]
                                                }}
                                            >
                                                {phase.priority}
                                            </span>
                                        </div>
                                        
                                        <div style={{ fontSize: '0.85rem', color: '#9ca3af' }}>
                                            {phase.items?.length || 0} items to address
                                        </div>
                                        
                                        {/* Show first 3 items */}
                                        <div style={{ marginTop: '1rem' }}>
                                            {phase.items?.slice(0, 3).map((item, itemIdx) => (
                                                <div 
                                                    key={itemIdx}
                                                    style={{
                                                        padding: '0.5rem',
                                                        background: 'rgba(0,0,0,0.2)',
                                                        borderRadius: '4px',
                                                        marginBottom: '0.5rem',
                                                        fontSize: '0.8rem'
                                                    }}
                                                >
                                                    <span style={{ color: FRAMEWORK_CONFIG[item.framework]?.color || '#ef4444' }}>
                                                        [{item.framework}]
                                                    </span>
                                                    {' '}{item.requirement_id}: {item.vulnerability}
                                                </div>
                                            ))}
                                            {phase.items?.length > 3 && (
                                                <div style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: '0.5rem' }}>
                                                    +{phase.items.length - 3} more items...
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

