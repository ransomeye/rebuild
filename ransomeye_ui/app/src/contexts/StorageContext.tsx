// Path and File Name : /home/ransomeye/rebuild/ransomeye_ui/app/src/contexts/StorageContext.tsx
// Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
// Details of functionality of this file: React context for IndexedDB storage access

import React, { createContext, useContext, ReactNode } from 'react'
import { storageService } from '../services/storage'

interface StorageContextType {
  storage: typeof storageService
}

const StorageContext = createContext<StorageContextType | undefined>(undefined)

export const StorageProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  return (
    <StorageContext.Provider value={{ storage: storageService }}>
      {children}
    </StorageContext.Provider>
  )
}

export const useStorage = (): StorageContextType => {
  const context = useContext(StorageContext)
  if (!context) {
    throw new Error('useStorage must be used within StorageProvider')
  }
  return context
}

