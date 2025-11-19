'use client'

import * as React from 'react'

type Theme = 'light' | 'dark' | 'system'

type ThemeProviderProps = {
  children: React.ReactNode
  defaultTheme?: Theme
  storageKey?: string
}

type ThemeProviderState = {
  theme: Theme
  setTheme: (theme: Theme) => void
  actualTheme: 'light' | 'dark'
}

const ThemeProviderContext = React.createContext<ThemeProviderState | undefined>(
  undefined
)

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  storageKey = 'nebenkosten-theme',
  ...props
}: ThemeProviderProps) {
  const [theme, setThemeState] = React.useState<Theme>(defaultTheme)
  const [mounted, setMounted] = React.useState(false)

  // Get the actual resolved theme (light or dark)
  const getResolvedTheme = React.useCallback((themeValue: Theme): 'light' | 'dark' => {
    if (themeValue === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    return themeValue
  }, [])

  const [actualTheme, setActualTheme] = React.useState<'light' | 'dark'>('light')

  React.useEffect(() => {
    setMounted(true)

    // Load theme from localStorage
    try {
      const storedTheme = localStorage.getItem(storageKey) as Theme | null
      if (storedTheme) {
        setThemeState(storedTheme)
      }
    } catch (e) {
      // localStorage might not be available
      console.warn('Failed to load theme from localStorage:', e)
    }
  }, [storageKey])

  React.useEffect(() => {
    if (!mounted) return

    const resolved = getResolvedTheme(theme)
    setActualTheme(resolved)

    const root = window.document.documentElement
    root.classList.remove('light', 'dark')
    root.classList.add(resolved)

    // Also set data-theme attribute for additional styling hooks
    root.setAttribute('data-theme', resolved)
  }, [theme, mounted, getResolvedTheme])

  // Listen for system theme changes when in system mode
  React.useEffect(() => {
    if (!mounted || theme !== 'system') return

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

    const handleChange = () => {
      const resolved = getResolvedTheme('system')
      setActualTheme(resolved)

      const root = window.document.documentElement
      root.classList.remove('light', 'dark')
      root.classList.add(resolved)
      root.setAttribute('data-theme', resolved)
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [theme, mounted, getResolvedTheme])

  const setTheme = React.useCallback(
    (newTheme: Theme) => {
      try {
        localStorage.setItem(storageKey, newTheme)
      } catch (e) {
        console.warn('Failed to save theme to localStorage:', e)
      }
      setThemeState(newTheme)
    },
    [storageKey]
  )

  const value = React.useMemo(
    () => ({
      theme,
      setTheme,
      actualTheme,
    }),
    [theme, setTheme, actualTheme]
  )

  // Prevent flash of wrong theme
  if (!mounted) {
    return <>{children}</>
  }

  return (
    <ThemeProviderContext.Provider {...props} value={value}>
      {children}
    </ThemeProviderContext.Provider>
  )
}

export const useTheme = () => {
  const context = React.useContext(ThemeProviderContext)

  if (context === undefined)
    throw new Error('useTheme must be used within a ThemeProvider')

  return context
}
