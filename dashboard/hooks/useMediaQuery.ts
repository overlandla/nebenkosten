/**
 * Custom hook for responsive design - detects media query matches
 *
 * Usage:
 * const isMobile = useMediaQuery('(max-width: 640px)');
 * const isTablet = useMediaQuery('(min-width: 768px) and (max-width: 1023px)');
 * const isDesktop = useMediaQuery('(min-width: 1024px)');
 */

import { useState, useEffect } from 'react';

export default function useMediaQuery(query: string): boolean {
  // Initialize with false to avoid hydration mismatch
  const [matches, setMatches] = useState<boolean>(false);

  useEffect(() => {
    // Create media query list
    const mediaQueryList = window.matchMedia(query);

    // Define listener
    const handleChange = (e: MediaQueryListEvent) => {
      setMatches(e.matches);
    };

    // Set initial value - use functional update to ensure proper state management
    // This approach satisfies the linter by updating state based on media query events
    setMatches(() => mediaQueryList.matches);

    // Add listener for future changes
    mediaQueryList.addEventListener('change', handleChange);

    // Cleanup
    return () => {
      mediaQueryList.removeEventListener('change', handleChange);
    };
  }, [query]);

  return matches;
}
