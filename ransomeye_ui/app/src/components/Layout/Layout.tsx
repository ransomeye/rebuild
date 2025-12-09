// Path and File Name : /home/ransomeye/rebuild/ransomeye_ui/app/src/components/Layout/Layout.tsx
// Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
// Details of functionality of this file: Main layout component with navigation and offline banner

import React, { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useApi } from '../../contexts/ApiContext'
import './Layout.css'

interface LayoutProps {
  children: ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { isOnline } = useApi()
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  return (
    <div className="app-container">
      {!isOnline && (
        <div className="offline-banner">
          ⚠️ Offline Mode - Read-only access to cached data
        </div>
      )}
      {isOnline && (
        <div className="offline-banner online">
          ✓ Online - Connected to backend
        </div>
      )}
      
      <header className="app-header">
        <div className="app-title">RansomEye</div>
        <nav className="app-nav">
          <Link 
            to="/dashboard" 
            className={isActive('/dashboard') ? 'nav-link active' : 'nav-link'}
          >
            Dashboard
          </Link>
          <Link 
            to="/alerts" 
            className={isActive('/alerts') ? 'nav-link active' : 'nav-link'}
          >
            Alerts
          </Link>
          <Link 
            to="/models" 
            className={isActive('/models') ? 'nav-link active' : 'nav-link'}
          >
            Models
          </Link>
          <Link 
            to="/dashboard/editor" 
            className={isActive('/dashboard/editor') ? 'nav-link active' : 'nav-link'}
          >
            Editor
          </Link>
        </nav>
      </header>
      
      <main className="app-content">
        {children}
      </main>
      
      <footer className="app-footer">
        <div>© RansomEye.Tech | Support: Gagan@RansomEye.Tech</div>
      </footer>
    </div>
  )
}

export default Layout

