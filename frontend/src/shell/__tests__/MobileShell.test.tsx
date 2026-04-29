import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MobileShell } from '../MobileShell'

describe('MobileShell', () => {
  beforeEach(() => {
    // Mock window.matchMedia for viewport detection
    window.matchMedia = vi.fn((query) => ({
      matches: query === '(max-width: 767px)',
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))
  })

  it('renders bottom tabs on mobile viewport', () => {
    const handleTabChange = vi.fn()
    render(
      <MobileShell currentTab="fleet" onTabChange={handleTabChange}>
        <div>Test Content</div>
      </MobileShell>
    )

    expect(screen.getByText('Fleet')).toBeInTheDocument()
    expect(screen.getByText('Workflows')).toBeInTheDocument()
    expect(screen.getByText('Remediation')).toBeInTheDocument()
    expect(screen.getByText('Maxwell')).toBeInTheDocument()
    expect(screen.getByText('More')).toBeInTheDocument()
  })

  it('highlights active tab', () => {
    const handleTabChange = vi.fn()
    render(
      <MobileShell currentTab="workflows" onTabChange={handleTabChange}>
        <div>Test Content</div>
      </MobileShell>
    )

    const workflowsTab = screen.getByText('Workflows').closest('button')
    expect(workflowsTab).toHaveStyle({ color: '#58a6ff' }) // accentBlue
  })

  it('calls onTabChange when tab is clicked', () => {
    const handleTabChange = vi.fn()
    render(
      <MobileShell currentTab="fleet" onTabChange={handleTabChange}>
        <div>Test Content</div>
      </MobileShell>
    )

    const workflowsTab = screen.getByText('Workflows')
    fireEvent.click(workflowsTab)

    expect(handleTabChange).toHaveBeenCalledWith('workflows')
  })

  it('opens drawer when More tab is clicked', async () => {
    const handleTabChange = vi.fn()
    render(
      <MobileShell currentTab="fleet" onTabChange={handleTabChange}>
        <div>Test Content</div>
      </MobileShell>
    )

    const moreTab = screen.getByText('More')
    fireEvent.click(moreTab)

    await waitFor(() => {
      expect(screen.getByText('Org')).toBeInTheDocument()
      expect(screen.getByText('Queue Health')).toBeInTheDocument()
    })
  })

  it('closes drawer when backdrop is clicked', async () => {
    const handleTabChange = vi.fn()
    const { container } = render(
      <MobileShell currentTab="fleet" onTabChange={handleTabChange}>
        <div>Test Content</div>
      </MobileShell>
    )

    // Open drawer
    const moreTab = screen.getByText('More')
    fireEvent.click(moreTab)

    await waitFor(() => {
      expect(screen.getByText('Org')).toBeInTheDocument()
    })

    // Click backdrop
    const overlay = container.querySelector('[style*="rgba(0, 0, 0, 0.5)"]')
    if (overlay) {
      fireEvent.click(overlay)
    }

    await waitFor(() => {
      expect(screen.queryByText('Org')).not.toBeInTheDocument()
    })
  })

  it('preserves component state when switching tabs', () => {
    const handleTabChange = vi.fn()
    const { rerender } = render(
      <MobileShell currentTab="fleet" onTabChange={handleTabChange}>
        <Counter />
      </MobileShell>
    )

    // Increment counter
    const incrementBtn = screen.getByText('+')
    fireEvent.click(incrementBtn)
    fireEvent.click(incrementBtn)

    expect(screen.getByText('Count: 2')).toBeInTheDocument()

    // Switch to different tab
    const workflowsTab = screen.getByText('Workflows')
    fireEvent.click(workflowsTab)

    // Re-render with same component mounted
    rerender(
      <MobileShell currentTab="workflows" onTabChange={handleTabChange}>
        <Counter />
      </MobileShell>
    )

    // State should be preserved
    expect(screen.getByText('Count: 2')).toBeInTheDocument()
  })

  it('does not show mobile shell on desktop viewport', () => {
    window.matchMedia = vi.fn((query) => ({
      matches: query !== '(max-width: 767px)',
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))

    const handleTabChange = vi.fn()
    render(
      <MobileShell currentTab="fleet" onTabChange={handleTabChange}>
        <div>Test Content</div>
      </MobileShell>
    )

    // Mobile nav should not be present on desktop
    expect(screen.queryByText('Fleet')).not.toBeInTheDocument()
  })
})

// Test helper component
function Counter() {
  const [count, setCount] = React.useState(0)
  return (
    <div>
      <div>Count: {count}</div>
      <button onClick={() => setCount(count + 1)}>+</button>
    </div>
  )
}
