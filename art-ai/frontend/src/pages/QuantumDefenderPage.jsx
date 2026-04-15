import React, { useState, useRef, useCallback } from 'react'
import './Pages.css'

const DEFAULT_NOVNC_URL = 'http://localhost:6080'

/* ── Inline SVG Icons ─────────────────────────────────────── */
const icons = {
    terminal: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="4 17 10 11 4 5" /><line x1="12" y1="19" x2="20" y2="19" />
        </svg>
    ),
    monitor: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
        </svg>
    ),
    link: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
        </svg>
    ),
    x: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
        </svg>
    ),
    refresh: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="23 4 23 10 17 10" /><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
        </svg>
    ),
    maximize: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
        </svg>
    ),
    minimize: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7" />
        </svg>
    ),
    chevronDown: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9" />
        </svg>
    ),
    chevronUp: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="18 15 12 9 6 15" />
        </svg>
    ),
    book: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        </svg>
    ),
    docker: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="1" y="11" width="4" height="3" rx="0.5" /><rect x="6" y="11" width="4" height="3" rx="0.5" /><rect x="11" y="11" width="4" height="3" rx="0.5" />
            <rect x="16" y="11" width="4" height="3" rx="0.5" /><rect x="6" y="7" width="4" height="3" rx="0.5" /><rect x="11" y="7" width="4" height="3" rx="0.5" />
            <rect x="11" y="3" width="4" height="3" rx="0.5" /><rect x="6" y="3" width="4" height="3" rx="0.5" />
            <path d="M22 13.5c-.5-1-1.5-1.5-3-1.5" />
        </svg>
    ),
    send: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
    ),
    /* Tool icons */
    crosshair: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" /><line x1="22" y1="12" x2="18" y2="12" /><line x1="6" y1="12" x2="2" y2="12" /><line x1="12" y1="6" x2="12" y2="2" /><line x1="12" y1="22" x2="12" y2="18" />
        </svg>
    ),
    globe: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
        </svg>
    ),
    database: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
        </svg>
    ),
    lock: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
    ),
    wifi: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12.55a11 11 0 0 1 14.08 0" /><path d="M1.42 9a16 16 0 0 1 21.16 0" /><path d="M8.53 16.11a6 6 0 0 1 6.95 0" /><line x1="12" y1="20" x2="12.01" y2="20" />
        </svg>
    ),
    zap: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
        </svg>
    ),
    shield: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
    ),
    key: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
        </svg>
    ),
    info: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
    ),
}

function QuantumDefenderPage() {
    const [kaliUrl, setKaliUrl] = useState(DEFAULT_NOVNC_URL)
    const [inputUrl, setInputUrl] = useState(DEFAULT_NOVNC_URL)
    const [isConnected, setIsConnected] = useState(false)
    const [isFullscreen, setIsFullscreen] = useState(false)
    const [showSetup, setShowSetup] = useState(false)
    const iframeRef = useRef(null)
    const containerRef = useRef(null)

    const connect = useCallback(() => {
        const url = inputUrl.trim()
        if (!url) return
        setKaliUrl(url)
        setIsConnected(true)
    }, [inputUrl])

    const disconnect = () => {
        setIsConnected(false)
    }

    const toggleFullscreen = () => {
        if (!containerRef.current) return
        if (!document.fullscreenElement) {
            containerRef.current.requestFullscreen()
            setIsFullscreen(true)
        } else {
            document.exitFullscreen()
            setIsFullscreen(false)
        }
    }

    const refreshInstance = () => {
        if (iframeRef.current) {
            iframeRef.current.src = kaliUrl
        }
    }

    const dockerCommands = [
        {
            label: 'Quick Start (Kasm Kali Desktop)',
            cmd: 'docker run -d --name kali-desktop -p 6080:6901 -e VNC_PW=kali --shm-size=512m kasmweb/kali-rolling-desktop:1.16.0',
            note: 'Access at https://localhost:6080 — default password: kali',
        },
        {
            label: 'LinuxServer Kali (Recommended)',
            cmd: 'docker run -d --name kali-web -p 6080:3000 --shm-size=1g lscr.io/linuxserver/kali-linux:latest',
            note: 'Access at http://localhost:6080',
        },
        {
            label: 'Custom Build (noVNC from scratch)',
            cmd: 'docker run -d --name kali-vnc -p 5900:5900 -p 6080:6080 kalilinux/kali-rolling bash -c "apt update && apt install -y novnc x11vnc xvfb kali-desktop-xfce && export DISPLAY=:1 && Xvfb :1 -screen 0 1280x720x24 & sleep 2 && startxfce4 & x11vnc -display :1 -forever -nopw -rfbport 5900 & /usr/share/novnc/utils/novnc_proxy --vnc localhost:5900 --listen 6080"',
            note: 'Builds from scratch — takes longer but fully customizable',
        },
    ]

    const tools = [
        { icon: icons.crosshair, name: 'Nmap', desc: 'Network scanner' },
        { icon: icons.globe, name: 'Burp Suite', desc: 'Web app testing' },
        { icon: icons.database, name: 'SQLMap', desc: 'SQL injection' },
        { icon: icons.lock, name: 'John the Ripper', desc: 'Password cracking' },
        { icon: icons.wifi, name: 'Wireshark', desc: 'Packet analysis' },
        { icon: icons.zap, name: 'Metasploit', desc: 'Exploitation' },
        { icon: icons.shield, name: 'Aircrack-ng', desc: 'WiFi security' },
        { icon: icons.key, name: 'Hydra', desc: 'Brute force' },
    ]

    return (
        <div className="page">
            {/* HUD Status Bar */}
            <div className="qd-hud-bar animate-fade-in">
                <div className="qd-hud-left">
                    <span className="qd-hud-label">SESSION</span>
                    <span className="qd-hud-value">{isConnected ? 'ACTIVE' : 'IDLE'}</span>
                </div>
                <div className="qd-hud-center">
                    <span className="qd-hud-label">TARGET</span>
                    <span className="qd-hud-value" style={{ fontFamily: "'Fira Code', monospace", fontSize: '0.72rem' }}>{isConnected ? kaliUrl : '—'}</span>
                </div>
                <div className="qd-hud-right">
                    <span className="qd-hud-label">STATUS</span>
                    <span className="qd-hud-status">
                        <span className="qd-status-dot" style={{
                            background: isConnected ? '#22c55e' : '#ff4444',
                            boxShadow: `0 0 6px ${isConnected ? '#22c55e' : '#ff4444'}`,
                        }} />
                        {isConnected ? 'CONNECTED' : 'DISCONNECTED'}
                    </span>
                </div>
            </div>

            {/* Header */}
            <div className="page-header" style={{ marginBottom: '1rem' }}>
                <h1 className="page-title" style={{ marginBottom: '0.25rem' }}>
                    <span className="page-title-icon" style={{ color: '#ef4444' }}>{icons.terminal}</span>
                    Kali Linux Instance
                </h1>
                <p className="page-subtitle" style={{ maxWidth: 520 }}>
                    Full Kali Linux desktop environment via noVNC + Docker
                </p>
            </div>

            {/* Tools strip */}
            <div className="qd-capabilities-strip animate-fade-in">
                {tools.map((tool, i) => (
                    <div key={i} className="qd-cap-chip">
                        <span className="qd-cap-icon">{tool.icon}</span>
                        <div>
                            <div className="qd-cap-title">{tool.name}</div>
                            <div className="qd-cap-desc">{tool.desc}</div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Connection bar */}
            <div className="card animate-fade-in" style={{ marginBottom: '1rem', padding: '1rem 1.25rem' }}>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'stretch', flexWrap: 'wrap' }}>
                    <input
                        type="text"
                        className="form-input qd-input"
                        value={inputUrl}
                        onChange={(e) => setInputUrl(e.target.value)}
                        placeholder="noVNC URL (e.g. http://localhost:6080)"
                        disabled={isConnected}
                        style={{ flex: 1, minWidth: 220, fontFamily: "'Fira Code', monospace", fontSize: '0.85rem' }}
                    />
                    {!isConnected ? (
                        <button type="button" className="btn qd-btn-send" onClick={connect} disabled={!inputUrl.trim()}>
                            {icons.link} <span style={{ marginLeft: 4 }}>Connect</span>
                        </button>
                    ) : (
                        <>
                            <button type="button" className="btn btn-secondary" onClick={refreshInstance} title="Refresh" style={{ padding: '0.5rem 0.75rem' }}>
                                {icons.refresh}
                            </button>
                            <button type="button" className="btn btn-secondary" onClick={toggleFullscreen} title="Fullscreen" style={{ padding: '0.5rem 0.75rem' }}>
                                {isFullscreen ? icons.minimize : icons.maximize}
                            </button>
                            <button type="button" className="btn qd-btn-cancel" onClick={disconnect}>
                                {icons.x} <span style={{ marginLeft: 4 }}>Disconnect</span>
                            </button>
                        </>
                    )}
                    <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => setShowSetup(!showSetup)}
                        style={{ fontSize: '0.85rem' }}
                    >
                        {showSetup ? icons.chevronUp : icons.chevronDown}
                        <span style={{ marginLeft: 4 }}>Setup Guide</span>
                    </button>
                </div>
            </div>

            {/* Setup Guide (collapsible) */}
            {showSetup && (
                <div className="card animate-fade-in" style={{ marginBottom: '1rem', padding: '1rem 1.25rem' }}>
                    <h2 className="card-title" style={{ marginBottom: '0.75rem' }}>
                        <span style={{ color: '#ef4444', display: 'flex', alignItems: 'center' }}>{icons.docker}</span>
                        Docker Setup Guide
                    </h2>
                    <p style={{ color: '#9ca3af', fontSize: '0.82rem', marginBottom: '1rem' }}>
                        Run one of these commands to start a Kali Linux desktop container, then click <strong>Connect</strong>.
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        {dockerCommands.map((cmd, i) => (
                            <div key={i} className="result-item" style={{ padding: '0.75rem' }}>
                                <div style={{ fontWeight: 600, color: '#fff', fontSize: '0.85rem', marginBottom: '0.35rem' }}>
                                    {cmd.label}
                                </div>
                                <div
                                    className="code-block"
                                    style={{
                                        fontSize: '0.78rem',
                                        cursor: 'pointer',
                                        marginBottom: '0.35rem',
                                    }}
                                    onClick={() => navigator.clipboard.writeText(cmd.cmd)}
                                    title="Click to copy"
                                >
                                    {cmd.cmd}
                                </div>
                                <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>{cmd.note}</div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Kali Desktop iframe / Empty state */}
            <div className="card animate-fade-in qd-chat-card" ref={containerRef} style={{ padding: 0, overflow: 'hidden' }}>
                {isConnected ? (
                    <iframe
                        ref={iframeRef}
                        src={kaliUrl}
                        title="Kali Linux Desktop"
                        style={{
                            width: '100%',
                            height: isFullscreen ? '100vh' : '70vh',
                            border: 'none',
                            borderRadius: '16px',
                            background: '#000',
                        }}
                        allow="clipboard-read; clipboard-write"
                    />
                ) : (
                    <div className="qd-empty-state" style={{ padding: '3rem 1rem' }}>
                        <div className="qd-empty-icon">
                            {icons.monitor}
                        </div>
                        <p className="qd-empty-title">Kali Linux Desktop</p>
                        <p className="qd-empty-subtitle" style={{ maxWidth: 520 }}>
                            Start a Kali Linux Docker container with noVNC, then enter the URL above and click{' '}
                            <strong style={{ color: '#ef4444' }}>Connect</strong> to launch a full desktop environment.
                        </p>
                        <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', marginTop: '1rem' }}>
                            <button type="button" className="btn qd-btn-send" onClick={() => setShowSetup(true)}>
                                {icons.book} <span style={{ marginLeft: 4 }}>View Setup Guide</span>
                            </button>
                            <button type="button" className="btn btn-secondary" onClick={connect}>
                                {icons.link} <span style={{ marginLeft: 4 }}>Connect to Default</span>
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Info footer */}
            <div className="card animate-fade-in" style={{ marginTop: '1rem', padding: '1rem', fontSize: '0.8rem', color: '#6b7280' }}>
                <span style={{ color: '#ef4444', marginRight: 6, display: 'inline-flex', verticalAlign: 'middle' }}>{icons.info}</span>
                <strong style={{ color: '#ef4444' }}>[Kali Instance]</strong>{' '}
                This page embeds a Kali Linux desktop running in Docker via noVNC. All pentesting tools (Nmap, Metasploit, Burp Suite, etc.)
                are available directly in the browser. Your session persists as long as the Docker container is running.
            </div>
        </div>
    )
}

export default QuantumDefenderPage

