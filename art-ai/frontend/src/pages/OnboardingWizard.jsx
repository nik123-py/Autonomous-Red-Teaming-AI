import React, { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTier } from '../components/TierContext'
import './OnboardingWizard.css'

/* ── tiny inline SVG icons ── */
const Icons = {
  Rocket: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/></svg>
  ),
  Building: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4"/><path d="M8 6h.01"/><path d="M16 6h.01"/><path d="M12 6h.01"/><path d="M12 10h.01"/><path d="M12 14h.01"/><path d="M16 10h.01"/><path d="M16 14h.01"/><path d="M8 10h.01"/><path d="M8 14h.01"/></svg>
  ),
  Crown: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14"/></svg>
  ),
  Eye: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>
  ),
  Users: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
  ),
  DollarSign: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
  ),
  Clock: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
  ),
  Shield: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
  ),
  Network: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="16" y="16" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="9" y="2" width="6" height="6" rx="1"/><path d="M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3"/><path d="M12 12V8"/></svg>
  ),
  FileCheck: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="m9 15 2 2 4-4"/></svg>
  ),
  Bug: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="8" height="14" x="8" y="6" rx="4"/><path d="m19 7-3 2"/><path d="m5 7 3 2"/><path d="m19 19-3-2"/><path d="m5 19 3-2"/><path d="M20 13h-4"/><path d="M4 13h4"/><path d="m10 4 1 2"/><path d="m14 4-1 2"/></svg>
  ),
  Crosshair: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="22" y1="12" x2="18" y2="12"/><line x1="6" y1="12" x2="2" y2="12"/><line x1="12" y1="6" x2="12" y2="2"/><line x1="12" y1="22" x2="12" y2="18"/></svg>
  ),
  Zap: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
  ),
  Check: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
  ),
  Lock: () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
  ),
  Unlock: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m9 15 2 2 4-4"/></svg>
  ),
  ArrowLeft: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
  ),
  ArrowRight: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
  ),
  Sparkles: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/></svg>
  ),
  Briefcase: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg>
  ),
  BarChart: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/></svg>
  ),
}

/* ── static data ── */
const BUSINESS_LEVELS = [
  {
    id: 'amateur',
    title: 'Amateur',
    desc: 'Development / Funding Phase — early-stage startup or side project',
    Icon: Icons.Rocket,
  },
  {
    id: 'intermediate',
    title: 'Intermediate',
    desc: 'Medium-level Startup — active revenue with a growing team',
    Icon: Icons.Building,
  },
  {
    id: 'pro',
    title: 'Pro',
    desc: 'High-level Enterprise — large workforce, strict compliance needs',
    Icon: Icons.Crown,
  },
  {
    id: 'checking',
    title: 'Just Checking',
    desc: 'Exploring security features — no commitment yet',
    Icon: Icons.Eye,
  },
]

const SECURITY_CONCERNS = [
  { id: 'network', label: 'Basic network scanning', desc: 'Port scanning & service discovery', Icon: Icons.Network },
  { id: 'compliance', label: 'Compliance & reporting', desc: 'SOC 2 / ISO / HIPAA dashboards', Icon: Icons.FileCheck },
  { id: 'vuln', label: 'Advanced vulnerability detection', desc: 'ML-powered vuln analysis', Icon: Icons.Bug },
  { id: 'redteam', label: 'Automated red teaming', desc: 'Autonomous penetration testing', Icon: Icons.Crosshair },
  { id: 'zeroday', label: 'Zero-day / exploit simulation', desc: 'Custom exploit generation', Icon: Icons.Zap },
]

const ALL_FEATURES = [
  { key: 'recon',       name: 'Network Recon Engine',          tiers: ['essential','advanced','elite'] },
  { key: 'vuln_basic',  name: 'Vulnerability Scanner',         tiers: ['essential','advanced','elite'] },
  { key: 'code',        name: 'Code Analysis (IVDetect)',       tiers: ['essential','advanced','elite'] },
  { key: 'exploit',     name: 'Exploit Generator',              tiers: ['advanced','elite'] },
  { key: 'compliance',  name: 'Compliance Mapper (SOC2/ISO)',   tiers: ['advanced','elite'] },
  { key: 'chat',        name: 'Pentest AI Chat',                tiers: ['advanced','elite'] },
  { key: 'rl',          name: 'RL Attack Agent (Q-Learning)',   tiers: ['elite'] },
  { key: 'ml',          name: 'ML Decision Maker',              tiers: ['elite'] },
  { key: 'quantum',     name: 'Quantum Defender',               tiers: ['elite'] },
]

const TIER_META = {
  essential: {
    badge: 'Essential Plan',
    title: 'Essential Security',
    tagline: 'Foundational protection at minimal cost — perfect for getting started.',
    badgeClass: 'essential',
  },
  advanced: {
    badge: 'Advanced Plan',
    title: 'Proactive Threat Detection',
    tagline: 'Deep scanning, compliance mapping, and AI-assisted analysis for growing teams.',
    badgeClass: 'advanced',
  },
  elite: {
    badge: 'Elite Plan',
    title: 'Full Autonomous Security',
    tagline: 'Unleash the complete ART-AI suite — RL agents, exploit generation, and quantum defence.',
    badgeClass: 'elite',
  },
}

/* ── tier computation ── */
function computeTier(businessLevel, metrics, concerns) {
  // direct level mapping
  if (businessLevel === 'pro') return 'elite'
  if (businessLevel === 'amateur' || businessLevel === 'checking') {
    // upgrade if metrics are high
    if (metrics.employees === '200+' && metrics.revenue === '$10M+') return 'elite'
    if ((metrics.employees === '50-200' || metrics.revenue === '$1M-$10M') &&
        (concerns.includes('redteam') || concerns.includes('zeroday'))) return 'advanced'
    return 'essential'
  }
  // intermediate
  if (concerns.includes('redteam') || concerns.includes('zeroday')) {
    if (metrics.employees === '200+' || metrics.revenue === '$10M+') return 'elite'
  }
  return 'advanced'
}

/* ════════════════════════════════════════════
   OnboardingWizard — main component
   ════════════════════════════════════════════ */
export default function OnboardingWizard() {
  const navigate = useNavigate()
  const { setTier: saveTier } = useTier()
  const [step, setStep] = useState(0)
  const [animKey, setAnimKey] = useState(0)

  // answers
  const [businessLevel, setBusinessLevel] = useState(null)
  const [metrics, setMetrics] = useState({ employees: '', revenue: '', lastCheckup: '' })
  const [concerns, setConcerns] = useState([])

  const goNext = useCallback(() => {
    setAnimKey(k => k + 1)
    setStep(s => Math.min(s + 1, 3))
  }, [])

  const goBack = useCallback(() => {
    setAnimKey(k => k + 1)
    setStep(s => Math.max(s - 1, 0))
  }, [])

  const toggleConcern = useCallback((id) => {
    setConcerns(prev => prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id])
  }, [])

  // determine whether "Next" should be enabled
  const canAdvance = () => {
    if (step === 0) return !!businessLevel
    if (step === 1) return metrics.employees && metrics.revenue && metrics.lastCheckup
    if (step === 2) return concerns.length > 0
    return false
  }

  const tier = computeTier(businessLevel, metrics, concerns)
  const tierInfo = TIER_META[tier]

  /* ── render helpers ── */

  const renderProgressBar = () => (
    <div className="onboarding-progress">
      {[0, 1, 2, 3].map((i) => (
        <div className="progress-step" key={i}>
          <div className={`progress-dot ${step === i ? 'active' : ''} ${step > i ? 'completed' : ''}`}>
            {step > i ? <Icons.Check /> : i + 1}
          </div>
          {i < 3 && <div className={`progress-line ${step > i ? 'filled' : ''}`} />}
        </div>
      ))}
    </div>
  )

  /* Step 1 ─ Business Level */
  const renderStep1 = () => (
    <div className="step-content" key={`s1-${animKey}`}>
      <h2 className="step-title">
        <span className="step-title-icon"><Icons.Briefcase /></span>
        Business Level Assessment
      </h2>
      <p className="step-subtitle">What describes your current business stage?</p>

      <div className="level-grid">
        {BUSINESS_LEVELS.map((lvl) => {
          const LvlIcon = lvl.Icon
          return (
            <div
              key={lvl.id}
              className={`level-card ${businessLevel === lvl.id ? 'selected' : ''}`}
              onClick={() => setBusinessLevel(lvl.id)}
            >
              <div className="level-card-check"><Icons.Check /></div>
              <div className="level-card-icon"><LvlIcon /></div>
              <div className="level-card-title">{lvl.title}</div>
              <div className="level-card-desc">{lvl.desc}</div>
            </div>
          )
        })}
      </div>
    </div>
  )

  /* Step 2 ─ Company Metrics */
  const renderStep2 = () => (
    <div className="step-content" key={`s2-${animKey}`}>
      <h2 className="step-title">
        <span className="step-title-icon"><Icons.BarChart /></span>
        Company Metrics
      </h2>
      <p className="step-subtitle">Help us understand the scale of your organisation.</p>

      <div className="metrics-grid">
        <div className="metric-group">
          <label className="metric-label">
            <span className="metric-label-icon"><Icons.Users /></span>
            Number of Employees
          </label>
          <select
            className="metric-select"
            value={metrics.employees}
            onChange={e => setMetrics(m => ({ ...m, employees: e.target.value }))}
          >
            <option value="">Select range…</option>
            <option value="1-10">1 – 10</option>
            <option value="11-50">11 – 50</option>
            <option value="50-200">50 – 200</option>
            <option value="200+">200+</option>
          </select>
        </div>

        <div className="metric-group">
          <label className="metric-label">
            <span className="metric-label-icon"><Icons.DollarSign /></span>
            Annual Revenue Generated
          </label>
          <select
            className="metric-select"
            value={metrics.revenue}
            onChange={e => setMetrics(m => ({ ...m, revenue: e.target.value }))}
          >
            <option value="">Select range…</option>
            <option value="Pre-revenue">Pre-revenue</option>
            <option value="<$1M">&lt; $1M</option>
            <option value="$1M-$10M">$1M – $10M</option>
            <option value="$10M+">$10M+</option>
          </select>
        </div>

        <div className="metric-group">
          <label className="metric-label">
            <span className="metric-label-icon"><Icons.Clock /></span>
            Last Security Checkup
          </label>
          <select
            className="metric-select"
            value={metrics.lastCheckup}
            onChange={e => setMetrics(m => ({ ...m, lastCheckup: e.target.value }))}
          >
            <option value="">Select an option…</option>
            <option value="Never">Never</option>
            <option value=">1 Year">&gt; 1 Year ago</option>
            <option value="Last 6 Months">Last 6 Months</option>
            <option value="Continuous">Continuous / Ongoing</option>
          </select>
        </div>
      </div>
    </div>
  )

  /* Step 3 ─ Security Concerns */
  const renderStep3 = () => (
    <div className="step-content" key={`s3-${animKey}`}>
      <h2 className="step-title">
        <span className="step-title-icon"><Icons.Shield /></span>
        Security Requirements
      </h2>
      <p className="step-subtitle">What are your primary security concerns today? (select all that apply)</p>

      <div className="concerns-grid">
        {SECURITY_CONCERNS.map((c) => {
          const CIcon = c.Icon
          const isActive = concerns.includes(c.id)
          return (
            <div
              key={c.id}
              className={`concern-toggle ${isActive ? 'active' : ''}`}
              onClick={() => toggleConcern(c.id)}
            >
              <div className="concern-checkbox">
                <Icons.Check />
              </div>
              <div className="concern-icon"><CIcon /></div>
              <div className="concern-info">
                <div className="concern-title">{c.label}</div>
                <div className="concern-desc">{c.desc}</div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )

  /* Step 4 ─ Recommendation */
  const renderStep4 = () => (
    <div className="step-content" key={`s4-${animKey}`}>
      <div className="result-section">
        <div className={`result-tier-badge ${tierInfo.badgeClass}`}>
          <Icons.Sparkles />
          {tierInfo.badge}
        </div>

        <h2 className="result-plan-title">{tierInfo.title}</h2>
        <p className="result-plan-tagline">{tierInfo.tagline}</p>

        <div className="result-features">
          {ALL_FEATURES.map((f) => {
            const unlocked = f.tiers.includes(tier)
            return (
              <div key={f.key} className={`result-feature ${unlocked ? 'unlocked' : 'locked'}`}>
                <div className="result-feature-icon">
                  {unlocked ? <Icons.Unlock /> : <Icons.Lock />}
                </div>
                <span className="result-feature-name">{f.name}</span>
                {!unlocked && (
                  <span className="result-feature-lock">
                    <Icons.Lock /> Locked
                  </span>
                )}
              </div>
            )
          })}
        </div>

        <button
          className="wizard-btn wizard-btn-provision"
          onClick={() => { saveTier(tier); navigate('/dashboard') }}
        >
          <Icons.Zap /> Provision Workspace
        </button>
      </div>
    </div>
  )

  const STEPS = [renderStep1, renderStep2, renderStep3, renderStep4]

  /* ── main render ── */
  return (
    <div className="onboarding-page">
      <div className="onboarding-container">
        <div className="onboarding-brand">
          <div className="onboarding-brand-title">
            <span>ART-AI</span> &mdash; Autonomous Red Team
          </div>
          <div className="onboarding-brand-sub">Security Posture Assessment</div>
        </div>

        {renderProgressBar()}

        <div className="wizard-card">
          {STEPS[step]()}

          {/* Navigation */}
          <div className="wizard-nav">
            {step > 0 && step < 3 ? (
              <button className="wizard-btn wizard-btn-back" onClick={goBack}>
                <Icons.ArrowLeft /> Back
              </button>
            ) : <div />}

            {step < 3 && (
              <button
                className="wizard-btn wizard-btn-next"
                disabled={!canAdvance()}
                onClick={goNext}
              >
                {step === 2 ? 'View Recommendation' : 'Continue'}
                <Icons.ArrowRight />
              </button>
            )}

            {step === 3 && (
              <button className="wizard-btn wizard-btn-back" onClick={goBack}>
                <Icons.ArrowLeft /> Re-assess
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
