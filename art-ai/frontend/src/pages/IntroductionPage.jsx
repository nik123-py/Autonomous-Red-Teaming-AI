import React from 'react'
import { Link } from 'react-router-dom'
import './IntroductionPage.css'

/* ── inline SVG icons (matching reference) ── */
const Icons = {
  ArrowRight: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>
  ),
  Shield: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>
  ),
  Zap: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>
  ),
  Brain: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z" /><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z" /></svg>
  ),
  Crosshair: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="22" y1="12" x2="18" y2="12" /><line x1="6" y1="12" x2="2" y2="12" /><line x1="12" y1="6" x2="12" y2="2" /><line x1="12" y1="22" x2="12" y2="18" /></svg>
  ),
  Code: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" /></svg>
  ),
  BarChart: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="20" x2="12" y2="10" /><line x1="18" y1="20" x2="18" y2="4" /><line x1="6" y1="20" x2="6" y2="16" /></svg>
  ),
}

const FEATURES = [
  { Icon: Icons.Zap, title: 'Network Scanner', desc: 'Port scanning, service discovery & OS fingerprinting' },
  { Icon: Icons.Shield, title: 'Vulnerability Scanner', desc: 'Multi-engine detection with ML-powered predictions' },
  { Icon: Icons.Crosshair, title: 'Exploit Generator', desc: '10+ exploit types: SQLi, XSS, RCE, SSRF & more' },
  { Icon: Icons.Code, title: 'Code Analysis', desc: 'C/C++ source vulnerability detection using ML' },
  { Icon: Icons.Brain, title: 'RL Agent', desc: 'Q-Learning with Exploit-DB guided intelligence' },
  { Icon: Icons.BarChart, title: 'Compliance Dashboard', desc: 'Security posture scoring & automated reports' },
]

const CAPABILITIES = [
  'Knowledge-Augmented Reinforcement Learning',
  'Learns from attack outcomes & Exploit-DB hints',
  'Autonomous 10-20 minute scheduling',
  'Interactive attack path visualization',
  'Real-time threat intelligence integration',
  'Multi-vector attack coordination',
]

const STATS = [
  { value: '20+', label: 'API Endpoints' },
  { value: '10+', label: 'Exploit Types' },
  { value: '10+', label: 'Attack Types' },
  { value: '12+', label: 'Dashboard Pages' },
]

export default function IntroductionPage() {
  return (
    <div className="intro-page">
      {/* ─── Navigation ─── */}
      <nav className="intro-nav">
        <div className="intro-nav-inner">
          <div className="intro-nav-brand">
            <div className="intro-nav-logo">⚔️</div>
            <span className="intro-nav-title">ART AI</span>
          </div>
          <Link to="/userassessment" className="intro-nav-cta">
            Get Started
          </Link>
        </div>
      </nav>

      {/* ─── Hero ─── */}
      <section className="intro-hero">
        <div>
          <div className="intro-hero-badge">🛡️ Autonomous Red Team AI</div>
          <h1>
            <span>Intelligent</span>
            <br />
            <span className="gradient-text">Security Testing</span>
          </h1>
          <p className="intro-hero-desc">
            Continuous, autonomous penetration testing powered by Knowledge-Augmented
            Reinforcement Learning. Discover vulnerabilities before attackers do.
          </p>
          <div className="intro-hero-actions">
            <Link to="/userassessment" className="intro-btn-primary">
              Launch Assessment <Icons.ArrowRight />
            </Link>
            <button className="intro-btn-secondary" onClick={() => {
              document.querySelector('.intro-features')?.scrollIntoView({ behavior: 'smooth' })
            }}>
              Learn More
            </button>
          </div>
          <div className="intro-hero-stats">
            <div>
              <div className="intro-stat-value">20+</div>
              <div className="intro-stat-label">API Endpoints</div>
            </div>
            <div>
              <div className="intro-stat-value">10+</div>
              <div className="intro-stat-label">Attack Types</div>
            </div>
            <div>
              <div className="intro-stat-value">100%</div>
              <div className="intro-stat-label">Autonomous</div>
            </div>
          </div>
        </div>

        <div className="intro-hero-visual">
          <div className="intro-hero-visual-glow" />
          <div className="intro-hero-visual-card">
            <div className="intro-visual-bar intro-visual-bar-red" />
            <div className="intro-visual-line" />
            <div className="intro-visual-line" style={{ width: '85%' }} />
            <div className="intro-visual-line" style={{ width: '70%' }} />
            <div style={{ height: '2rem' }} />
            <div className="intro-visual-line" style={{ width: '50%' }} />
            <div className="intro-visual-line" style={{ width: '65%' }} />
            <div className="intro-visual-dots">
              <div className="intro-visual-dot intro-visual-dot-green" />
              <div className="intro-visual-dot intro-visual-dot-red" />
              <div className="intro-visual-dot intro-visual-dot-yellow" />
            </div>
          </div>
        </div>
      </section>

      {/* ─── Features ─── */}
      <section className="intro-features">
        <div className="intro-features-inner">
          <div className="intro-section-header">
            <h2>Pentester Toolkit</h2>
            <p>Complete autonomous red teaming platform with intelligent AI-driven attack simulation</p>
          </div>
          <div className="intro-features-grid">
            {FEATURES.map((f, i) => {
              const FIcon = f.Icon
              return (
                <div key={i} className="intro-feature-card">
                  <div className="intro-feature-icon"><FIcon /></div>
                  <div className="intro-feature-title">{f.title}</div>
                  <div className="intro-feature-desc">{f.desc}</div>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ─── Capabilities ─── */}
      <section className="intro-capabilities">
        <div>
          <h2>AI-Powered Attack Simulation</h2>
          <ul className="intro-cap-list">
            {CAPABILITIES.map((cap, i) => (
              <li key={i} className="intro-cap-item">
                <div className="intro-cap-bullet">
                  <div className="intro-cap-bullet-inner" />
                </div>
                <span>{cap}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="intro-stats-grid">
          {STATS.map((s, i) => (
            <div key={i} className="intro-stat-box">
              <div className="intro-stat-box-value">{s.value}</div>
              <div className="intro-stat-box-label">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="intro-cta">
        <div className="intro-cta-inner">
          <h2>Ready to Start Testing?</h2>
          <p>
            Launch the autonomous red team AI platform and discover vulnerabilities
            before they become security incidents.
          </p>
          <Link to="/userassessment" className="intro-btn-primary">
            Enter Assessment <Icons.ArrowRight />
          </Link>
        </div>
      </section>

      {/* ─── Footer ─── */}
      <footer className="intro-footer">
        <div className="intro-footer-inner">
          <div className="intro-footer-brand">
            <div className="intro-footer-logo">⚔️</div>
            <span className="intro-footer-name">ART AI</span>
          </div>
          <p className="intro-footer-copy">© 2026 ART AI. Autonomous Red Team Intelligence.</p>
        </div>
      </footer>
    </div>
  )
}
