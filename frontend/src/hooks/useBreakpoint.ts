import { useState, useEffect } from 'react'
import { breakpoints } from '../design/breakpoints'

/**
 * React hook for responsive breakpoints with resize listener.
 * Returns the current breakpoint key based on window width.
 */
export function useBreakpoint(): keyof typeof breakpoints {
  const [breakpoint, setBreakpoint] = useState<keyof typeof breakpoints>(
    getBreakpoint(typeof window !== 'undefined' ? window.innerWidth : 1280)
  )

  useEffect(() => {
    const handleResize = () => {
      setBreakpoint(getBreakpoint(window.innerWidth))
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return breakpoint
}

function getBreakpoint(width: number): keyof typeof breakpoints {
  if (width <= breakpoints.xs) return 'xs'
  if (width <= breakpoints.sm) return 'sm'
  if (width <= breakpoints.md) return 'md'
  if (width <= breakpoints.lg) return 'lg'
  return 'xl'
}
