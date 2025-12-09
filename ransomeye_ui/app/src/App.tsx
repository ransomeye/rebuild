// Path and File Name : /home/ransomeye/rebuild/ransomeye_ui/app/src/App.tsx
// Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
// Details of functionality of this file: Main React application component with routing

import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout/Layout'
import Dashboard from './pages/Dashboard/Dashboard'
import DashboardEditor from './components/Editor/DashboardEditor'
import ModelList from './components/ModelRegistry/ModelList'
import AlertsView from './pages/Alerts/AlertsView'
import { StorageProvider } from './contexts/StorageContext'
import { ApiProvider } from './contexts/ApiContext'
import './App.css'

function App() {
  return (
    <StorageProvider>
      <ApiProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/dashboard/editor" element={<DashboardEditor />} />
            <Route path="/alerts" element={<AlertsView />} />
            <Route path="/models" element={<ModelList />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </ApiProvider>
    </StorageProvider>
  )
}

export default App

