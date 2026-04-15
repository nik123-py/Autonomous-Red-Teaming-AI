/**
 * Report Generation Page
 * Professional PDF/HTML security assessment reports
 * Includes executive summary, technical findings, risk scoring, and compliance mapping
 */

import React, { useState, useEffect } from 'react';
import { 
    DocumentIcon, 
    DownloadIcon, 
    ChartIcon 
} from '../components/Icons';

const API_BASE = 'http://localhost:8003';

// Risk level colors
const RISK_COLORS = {
    'Critical': '#ff4444',
    'High': '#ff8800',
    'Medium': '#ffaa00',
    'Low': '#22c55e'
};

export default function ReportGenerationPage() {
    // State management
    const [reportData, setReportData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState(null);
    const [previewMode, setPreviewMode] = useState('json');
    const [config, setConfig] = useState({
        target: 'Security Assessment Target',
        includeCompliance: true,
        frameworks: ['PCI-DSS', 'HIPAA', 'SOC2', 'ISO27001']
    });

    // Generate report from latest simulation
    const generateReport = async () => {
        setGenerating(true);
        setError(null);

        try {
            const response = await fetch(`${API_BASE}/api/reports/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    target: config.target,
                    include_compliance: config.includeCompliance,
                    frameworks: config.frameworks
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to generate report');
            }

            const data = await response.json();
            setReportData(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setGenerating(false);
        }
    };

    // Generate latest report on initial load
    const loadLatestReport = async () => {
        setLoading(true);
        try {
            const response = await fetch(`${API_BASE}/api/reports/latest`);
            if (response.ok) {
                const data = await response.json();
                setReportData(data);
            }
        } catch (err) {
            console.log('No existing report found');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadLatestReport();
    }, []);

    // Download HTML report
    const downloadReport = () => {
        if (!reportData?.html_report) return;

        const blob = new Blob([reportData.html_report], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `security-report-${reportData.report_id}.html`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    // Toggle framework in config
    const toggleFramework = (framework) => {
        setConfig(prev => ({
            ...prev,
            frameworks: prev.frameworks.includes(framework)
                ? prev.frameworks.filter(f => f !== framework)
                : [...prev.frameworks, framework]
        }));
    };

    return (
        <div className="page">
            {/* Header */}
            <div className="page-header">
                <h1 className="page-title">
                    <span className="page-title-icon">
                        <DocumentIcon size={28} color="#ef4444" />
                    </span>
                    Report Generation
                </h1>
                <p className="page-subtitle">
                    Generate professional security assessment reports with executive summaries and compliance mapping
                </p>
            </div>

            {/* Configuration Card */}
            <div className="card" style={{ marginBottom: '1.5rem' }}>
                <div className="card-header">
                    <h3 className="card-title">Report Configuration</h3>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                            className="btn btn-primary"
                            onClick={generateReport}
                            disabled={generating}
                        >
                            {generating ? (
                                <>
                                    <span className="loading-spinner" />
                                    Generating...
                                </>
                            ) : (
                                <>Generate Report</>
                            )}
                        </button>
                        {reportData && (
                            <button
                                className="btn btn-success"
                                onClick={downloadReport}
                            >
                                <DownloadIcon size={16} /> Download HTML
                            </button>
                        )}
                    </div>
                </div>

                <div className="grid-2" style={{ gap: '1.5rem' }}>
                    {/* Target Name */}
                    <div className="form-group">
                        <label className="form-label">Target System Name</label>
                        <input
                            type="text"
                            className="form-input"
                            value={config.target}
                            onChange={(e) => setConfig(prev => ({ ...prev, target: e.target.value }))}
                            placeholder="e.g., Production Web Server"
                        />
                    </div>

                    {/* Compliance Toggle */}
                    <div className="form-group">
                        <label className="form-label">Include Compliance Mapping</label>
                        <div
                            onClick={() => setConfig(prev => ({ ...prev, includeCompliance: !prev.includeCompliance }))}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.75rem',
                                padding: '0.75rem 1rem',
                                background: config.includeCompliance ? 'rgba(0,212,255,0.1)' : 'rgba(0,0,0,0.2)',
                                border: `1px solid ${config.includeCompliance ? 'rgba(0,212,255,0.4)' : 'rgba(255,255,255,0.1)'}`,
                                borderRadius: '8px',
                                cursor: 'pointer'
                            }}
                        >
                            <div style={{
                                width: '20px',
                                height: '20px',
                                borderRadius: '4px',
                                background: config.includeCompliance ? '#ef4444' : 'transparent',
                                border: `2px solid ${config.includeCompliance ? '#ef4444' : '#6b7280'}`,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}>
                                {config.includeCompliance && (
                                    <span style={{ color: '#0a0e27', fontSize: '14px', fontWeight: 'bold' }}>✓</span>
                                )}
                            </div>
                            <span style={{ color: config.includeCompliance ? '#ef4444' : '#9ca3af' }}>
                                Map findings to compliance frameworks
                            </span>
                        </div>
                    </div>
                </div>

                {/* Framework Selection */}
                {config.includeCompliance && (
                    <div style={{ marginTop: '1rem' }}>
                        <label className="form-label">Compliance Frameworks</label>
                        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                            {['PCI-DSS', 'HIPAA', 'SOC2', 'ISO27001'].map(framework => (
                                <div
                                    key={framework}
                                    onClick={() => toggleFramework(framework)}
                                    style={{
                                        padding: '0.5rem 1rem',
                                        background: config.frameworks.includes(framework)
                                            ? 'rgba(0,212,255,0.15)'
                                            : 'rgba(0,0,0,0.2)',
                                        border: `1px solid ${config.frameworks.includes(framework) ? 'rgba(0,212,255,0.4)' : 'rgba(255,255,255,0.1)'}`,
                                        borderRadius: '20px',
                                        cursor: 'pointer',
                                        color: config.frameworks.includes(framework) ? '#ef4444' : '#9ca3af',
                                        fontSize: '0.85rem',
                                        fontWeight: 500
                                    }}
                                >
                                    {framework}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Error Display */}
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

            {/* Report Results */}
            {reportData && (
                <>
                    {/* Report Summary Stats */}
                    <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
                        <div className="stat-card">
                            <div 
                                className="stat-value" 
                                style={{ color: RISK_COLORS[reportData.risk_metrics?.risk_level] || '#ef4444' }}
                            >
                                {reportData.risk_metrics?.overall_risk_score || 0}
                            </div>
                            <div className="stat-label">Risk Score</div>
                        </div>
                        <div className="stat-card">
                            <div 
                                className="stat-value" 
                                style={{ color: RISK_COLORS[reportData.risk_metrics?.risk_level] || '#ef4444' }}
                            >
                                {reportData.risk_metrics?.risk_level || 'N/A'}
                            </div>
                            <div className="stat-label">Risk Level</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value" style={{ color: '#ff4444' }}>
                                {reportData.risk_metrics?.vulnerability_count || 0}
                            </div>
                            <div className="stat-label">Vulnerabilities</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value" style={{ 
                                color: reportData.risk_metrics?.access_level_achieved === 'admin' ? '#ff4444' : '#22c55e' 
                            }}>
                                {reportData.risk_metrics?.access_level_achieved?.toUpperCase() || 'NONE'}
                            </div>
                            <div className="stat-label">Access Achieved</div>
                        </div>
                    </div>

                    {/* View Mode Tabs */}
                    <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
                        <button
                            className={`btn ${previewMode === 'json' ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setPreviewMode('json')}
                        >
                            Report Data
                        </button>
                        <button
                            className={`btn ${previewMode === 'preview' ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setPreviewMode('preview')}
                        >
                            HTML Preview
                        </button>
                        <button
                            className={`btn ${previewMode === 'findings' ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setPreviewMode('findings')}
                        >
                            Technical Findings
                        </button>
                        <button
                            className={`btn ${previewMode === 'remediation' ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setPreviewMode('remediation')}
                        >
                            Remediation
                        </button>
                    </div>

                    {/* JSON Data View */}
                    {previewMode === 'json' && (
                        <div className="card">
                            <h3 className="card-title" style={{ marginBottom: '1rem' }}>
                                <ChartIcon size={20} color="#ef4444" /> Executive Summary
                            </h3>
                            <div style={{
                                padding: '1rem',
                                background: 'rgba(0,0,0,0.3)',
                                borderRadius: '8px',
                                color: '#e0e0e0',
                                whiteSpace: 'pre-wrap',
                                lineHeight: '1.7',
                                fontSize: '0.9rem'
                            }}>
                                {reportData.executive_summary}
                            </div>

                            {/* Compliance Scores */}
                            {reportData.compliance_scores && Object.keys(reportData.compliance_scores).length > 0 && (
                                <div style={{ marginTop: '1.5rem' }}>
                                    <h4 style={{ color: '#fff', marginBottom: '1rem' }}>Compliance Scores</h4>
                                    <div className="grid-4">
                                        {Object.entries(reportData.compliance_scores).map(([framework, score]) => (
                                            <div 
                                                key={framework}
                                                style={{
                                                    padding: '1rem',
                                                    background: 'rgba(0,0,0,0.2)',
                                                    borderRadius: '8px',
                                                    textAlign: 'center'
                                                }}
                                            >
                                                <div style={{ 
                                                    fontSize: '1.5rem', 
                                                    fontWeight: 'bold',
                                                    color: score.score >= 80 ? '#22c55e' : score.score >= 60 ? '#ffaa00' : '#ff4444'
                                                }}>
                                                    {score.score.toFixed(1)}%
                                                </div>
                                                <div style={{ fontSize: '0.8rem', color: '#9ca3af' }}>{framework}</div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Report metadata */}
                            <div style={{ 
                                marginTop: '1.5rem',
                                padding: '1rem',
                                background: 'rgba(0,212,255,0.05)',
                                borderRadius: '8px',
                                fontSize: '0.85rem',
                                color: '#9ca3af'
                            }}>
                                <div><strong>Report ID:</strong> {reportData.report_id}</div>
                                <div><strong>Generated:</strong> {new Date(reportData.generated_at).toLocaleString()}</div>
                                <div><strong>Target:</strong> {reportData.target}</div>
                            </div>
                        </div>
                    )}

                    {/* HTML Preview */}
                    {previewMode === 'preview' && (
                        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                            <iframe
                                srcDoc={reportData.html_report}
                                style={{
                                    width: '100%',
                                    height: '800px',
                                    border: 'none',
                                    borderRadius: '16px'
                                }}
                                title="Report Preview"
                            />
                        </div>
                    )}

                    {/* Technical Findings */}
                    {previewMode === 'findings' && (
                        <div className="card">
                            <h3 className="card-title" style={{ marginBottom: '1rem' }}>
                                Technical Findings ({reportData.technical_findings?.length || 0})
                            </h3>
                            <div className="results-list">
                                {reportData.technical_findings?.map((finding, idx) => (
                                    <div key={idx} className="result-item">
                                        <div className="result-item-header">
                                            <span className="result-item-title">{finding.title}</span>
                                            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                                <span style={{
                                                    padding: '0.25rem 0.5rem',
                                                    background: 'rgba(0,212,255,0.15)',
                                                    color: '#ef4444',
                                                    borderRadius: '4px',
                                                    fontSize: '0.75rem'
                                                }}>
                                                    CVSS: {finding.cvss_score}
                                                </span>
                                                <span 
                                                    className="badge"
                                                    style={{ 
                                                        background: `${RISK_COLORS[finding.severity]}20`,
                                                        color: RISK_COLORS[finding.severity]
                                                    }}
                                                >
                                                    {finding.severity}
                                                </span>
                                            </div>
                                        </div>
                                        <div style={{ fontSize: '0.85rem', color: '#9ca3af', marginBottom: '0.5rem' }}>
                                            {finding.description}
                                        </div>
                                        <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>
                                            <strong style={{ color: '#ff8800' }}>Impact:</strong> {finding.impact}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Remediation */}
                    {previewMode === 'remediation' && (
                        <div className="card">
                            <h3 className="card-title" style={{ marginBottom: '1rem' }}>
                                Remediation Recommendations
                            </h3>
                            <div className="results-list">
                                {reportData.remediation?.map((rec, idx) => (
                                    <div 
                                        key={idx} 
                                        className="result-item"
                                        style={{ 
                                            borderLeft: `4px solid ${rec.priority === 1 ? '#ff4444' : rec.priority === 2 ? '#ff8800' : '#ffaa00'}` 
                                        }}
                                    >
                                        <div className="result-item-header">
                                            <span className="result-item-title">
                                                P{rec.priority}: {rec.vulnerability}
                                            </span>
                                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                                <span style={{
                                                    padding: '0.25rem 0.75rem',
                                                    background: 'rgba(0,212,255,0.15)',
                                                    color: '#ef4444',
                                                    borderRadius: '20px',
                                                    fontSize: '0.75rem'
                                                }}>
                                                    {rec.timeline}
                                                </span>
                                                <span style={{
                                                    padding: '0.25rem 0.75rem',
                                                    background: 'rgba(255,255,255,0.1)',
                                                    color: '#9ca3af',
                                                    borderRadius: '20px',
                                                    fontSize: '0.75rem'
                                                }}>
                                                    Effort: {rec.effort}
                                                </span>
                                            </div>
                                        </div>
                                        <div style={{ 
                                            fontSize: '0.9rem', 
                                            color: '#22c55e', 
                                            marginBottom: '0.5rem',
                                            fontWeight: 500
                                        }}>
                                            {rec.recommendation}
                                        </div>
                                        <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>
                                            {rec.details}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* Loading state */}
            {loading && !reportData && (
                <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
                    <span className="loading-spinner" style={{ width: '40px', height: '40px' }} />
                    <p style={{ color: '#9ca3af', marginTop: '1rem' }}>Loading report data...</p>
                </div>
            )}

            {/* No data state */}
            {!loading && !reportData && !error && (
                <div className="card empty-state">
                    <div className="empty-state-icon">📄</div>
                    <div className="empty-state-title">No Report Generated</div>
                    <p style={{ color: '#6b7280' }}>
                        Configure your report settings and click "Generate Report" to create a security assessment report.
                    </p>
                </div>
            )}
        </div>
    );
}

