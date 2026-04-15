import React, { createContext, useContext, useState, useCallback } from 'react'

/**
 * TierContext
 * -----------
 * Stores the user's selected service tier ('essential' | 'advanced' | 'elite' | null).
 * Persisted in localStorage so it survives page refreshes.
 *
 * Each route has a `minTier` requirement; the helper `hasAccess` checks whether
 * the current tier meets or exceeds that requirement.
 */

const TIER_ORDER = ['essential', 'advanced', 'elite']

const TierContext = createContext({
  tier: null,
  setTier: () => {},
  hasAccess: () => false,
  clearTier: () => {},
})

export function TierProvider({ children }) {
  const [tier, setTierState] = useState(() => {
    try { return localStorage.getItem('art_ai_tier') || null }
    catch { return null }
  })

  const setTier = useCallback((t) => {
    setTierState(t)
    try { localStorage.setItem('art_ai_tier', t) } catch {}
  }, [])

  const clearTier = useCallback(() => {
    setTierState(null)
    try { localStorage.removeItem('art_ai_tier') } catch {}
  }, [])

  /** Returns true if the user's tier >= the required tier */
  const hasAccess = useCallback((requiredTier) => {
    if (!tier) return false
    return TIER_ORDER.indexOf(tier) >= TIER_ORDER.indexOf(requiredTier)
  }, [tier])

  return (
    <TierContext.Provider value={{ tier, setTier, hasAccess, clearTier }}>
      {children}
    </TierContext.Provider>
  )
}

export function useTier() {
  return useContext(TierContext)
}

/**
 * Route → minimum tier mapping.
 * If a route is NOT listed here it is accessible to all tiers.
 */
export const ROUTE_TIER_MAP = {
  '/dashboard':       'essential',
  '/network-scan':    'essential',
  '/vuln-scan':       'essential',
  '/code-analysis':   'essential',
  '/compliance':      'essential',
  '/reports':         'essential',
  '/attack-history':  'essential',
  '/exploits':        'advanced',
  '/pentest-chat':    'advanced',
  '/simulation':      'elite',
  '/rl-agent':        'elite',
  '/autonomous':      'elite',
  '/quantumdefender': 'elite',
}

export default TierContext
