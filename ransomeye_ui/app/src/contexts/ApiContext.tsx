// Path and File Name : /home/ransomeye/rebuild/ransomeye_ui/app/src/contexts/ApiContext.tsx
// Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
// Details of functionality of this file: React context for API service access

import React, { createContext, useContext, ReactNode, useState, useEffect } from 'react'
import { apiService } from '../services/api'

interface ApiContextType {
  api: typeof apiService
  isOnline: boolean
  refreshOnlineStatus: () => void
}

const ApiContext = createContext<ApiContextType | undefined>(undefined)

export const ApiProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isOnline, setIsOnline] = useState(navigator.onLine)

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    // Periodically check API health
    const healthCheck = setInterval(async () => {
      const healthy = await apiService.checkHealth()
      setIsOnline(healthy && navigator.onLine)
    }, 30000) // Check every 30 seconds

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
      clearInterval(healthCheck)
    }
  }, [])

  const refreshOnlineStatus = async () => {
    const healthy = await apiService.checkHealth()
    setIsOnline(healthy && navigator.onLine)
  }

  return (
    <ApiContext.Provider value={{ api: apiService, isOnline, refreshOnlineStatus }}>
      {children}
    </ApiContext.Provider>
  )
}

export const useApi = (): ApiContextType => {
  const context = useContext(ApiContext)
  if (!context) {
    throw new Error('useApi must be used within ApiProvider')
  }
  return context
}

