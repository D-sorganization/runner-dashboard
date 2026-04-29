import React, { useState, useMemo, ReactNode } from 'react'
import { useBreakpoint } from '../hooks/useBreakpoint'
import { breakpoints } from '../design/breakpoints'
import { colorTokens, spacingTokens, touchTokens } from '../design/tokens'

export type TabId = 'fleet' | 'workflows' | 'remediation' | 'maxwell' | 'more'

export interface MobileShellProps {
  children: ReactNode
  currentTab: TabId
  onTabChange: (tab: TabId) => void
  tabContent?: Record<TabId, ReactNode>
}

export function MobileShell({ children, currentTab, onTabChange }: MobileShellProps) {
  const breakpoint = useBreakpoint()
  const isMobile = breakpoint !== 'lg' && breakpoint !== 'xl'
  const [drawerOpen, setDrawerOpen] = useState(false)

  // Main tabs visible on bottom nav (5 primary tabs)
  const mainTabs: Array<{ id: TabId; label: string; icon: string }> = [
    { id: 'fleet', label: 'Fleet', icon: '⚡' },
    { id: 'workflows', label: 'Workflows', icon: '⚙️' },
    { id: 'remediation', label: 'Remediation', icon: '🔧' },
    { id: 'maxwell', label: 'Maxwell', icon: '🤖' },
    { id: 'more', label: 'More', icon: '⋯' },
  ]

  // Additional tabs in drawer (shown on "More" tab)
  const drawerTabs = [
    { id: 'org', label: 'Org' },
    { id: 'heavy', label: 'Heavy Runners' },
    { id: 'assessments', label: 'Assessments' },
    { id: 'requests', label: 'Feature Requests' },
    { id: 'credentials', label: 'Credentials' },
    { id: 'reports', label: 'Reports' },
    { id: 'health', label: 'Queue Health' },
  ]

  const handleTabClick = (tabId: TabId) => {
    onTabChange(tabId)
    if (tabId === 'more') {
      setDrawerOpen(true)
    }
  }

  // Only show mobile shell on small viewports
  if (!isMobile) {
    return <>{children}</>
  }

  return (
    <div style={styles.container}>
      {/* Main content area */}
      <div style={styles.content}>
        {children}
      </div>

      {/* Bottom Tab Bar */}
      <nav style={styles.navBar}>
        {mainTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabClick(tab.id)}
            style={{
              ...styles.tabButton,
              ...(currentTab === tab.id ? styles.tabButtonActive : {}),
            }}
            title={tab.label}
          >
            <span style={styles.tabIcon}>{tab.icon}</span>
            <span style={styles.tabLabel}>{tab.label}</span>
          </button>
        ))}
      </nav>

      {/* Drawer for additional tabs */}
      {drawerOpen && (
        <div style={styles.drawerOverlay} onClick={() => setDrawerOpen(false)}>
          <div style={styles.drawer} onClick={(e) => e.stopPropagation()}>
            <div style={styles.drawerHeader}>
              <button style={styles.drawerClose} onClick={() => setDrawerOpen(false)}>
                ✕
              </button>
            </div>
            <div style={styles.drawerContent}>
              {drawerTabs.map((tab) => (
                <button
                  key={tab.id}
                  style={styles.drawerItem}
                  onClick={() => {
                    setDrawerOpen(false)
                    // Handle drawer tab selection
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100vh',
    width: '100%',
    backgroundColor: colorTokens.bgPrimary,
  },

  content: {
    flex: 1,
    overflow: 'auto',
    paddingBottom: `calc(${touchTokens.bottomNavHeight} + env(safe-area-inset-bottom))`,
  },

  navBar: {
    display: 'flex',
    justifyContent: 'space-around',
    alignItems: 'center',
    height: touchTokens.bottomNavHeight,
    backgroundColor: colorTokens.bgSecondary,
    borderTop: `1px solid ${colorTokens.border}`,
    position: 'fixed' as const,
    bottom: 0,
    left: 0,
    right: 0,
    paddingBottom: 'env(safe-area-inset-bottom)',
    zIndex: 100,
  },

  tabButton: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacingTokens[1],
    flex: 1,
    height: '100%',
    background: 'none',
    border: 'none',
    color: colorTokens.textSecondary,
    cursor: 'pointer',
    fontSize: '12px',
    padding: 0,
    transition: 'color 0.2s',
  },

  tabButtonActive: {
    color: colorTokens.accentBlue,
  },

  tabIcon: {
    fontSize: '20px',
  },

  tabLabel: {
    fontSize: '11px',
    fontWeight: 500 as const,
  },

  drawerOverlay: {
    position: 'fixed' as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    zIndex: 200,
    animation: 'fadeIn 0.2s ease-out',
  },

  drawer: {
    position: 'fixed' as const,
    left: 0,
    top: 0,
    bottom: 0,
    width: '280px',
    backgroundColor: colorTokens.bgSecondary,
    borderRight: `1px solid ${colorTokens.border}`,
    display: 'flex',
    flexDirection: 'column' as const,
    zIndex: 201,
    animation: 'slideInLeft 0.3s ease-out',
  },

  drawerHeader: {
    display: 'flex',
    justifyContent: 'flex-end',
    alignItems: 'center',
    height: '56px',
    paddingRight: spacingTokens[4],
    borderBottom: `1px solid ${colorTokens.border}`,
  },

  drawerClose: {
    background: 'none',
    border: 'none',
    color: colorTokens.textPrimary,
    fontSize: '20px',
    cursor: 'pointer',
    padding: spacingTokens[2],
    minWidth: touchTokens.minimumHitTarget,
    minHeight: touchTokens.minimumHitTarget,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },

  drawerContent: {
    flex: 1,
    overflow: 'auto',
    display: 'flex',
    flexDirection: 'column' as const,
  },

  drawerItem: {
    padding: `${spacingTokens[4]} ${spacingTokens[4]}`,
    background: 'none',
    border: 'none',
    borderBottom: `1px solid ${colorTokens.border}`,
    color: colorTokens.textPrimary,
    textAlign: 'left' as const,
    cursor: 'pointer',
    minHeight: touchTokens.minimumHitTarget,
    display: 'flex',
    alignItems: 'center',
    fontSize: '14px',
    transition: 'backgroundColor 0.2s',
  },
}
