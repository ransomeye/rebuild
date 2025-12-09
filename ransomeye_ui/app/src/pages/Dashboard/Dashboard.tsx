// Path and File Name : /home/ransomeye/rebuild/ransomeye_ui/app/src/pages/Dashboard/Dashboard.tsx
// Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
// Details of functionality of this file: Main dashboard page with grid layout

import React, { useState, useEffect } from 'react'
import { Responsive, WidthProvider } from 'react-grid-layout'
import { useStorage } from '../../contexts/StorageContext'
import { useApi } from '../../contexts/ApiContext'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import './Dashboard.css'

const ResponsiveGridLayout = WidthProvider(Responsive)

const Dashboard: React.FC = () => {
  const { storage } = useStorage()
  const { api } = useApi()
  const [dashboard, setDashboard] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboard()
  }, [])

  const loadDashboard = async () => {
    try {
      // Try to get default dashboard
      let defaultDashboard = await storage.storage.getDefaultDashboard()
      
      // If no default, try API
      if (!defaultDashboard) {
        try {
          const dashboards = await api.api.getDashboards()
          defaultDashboard = dashboards.find((d: any) => d.is_default) || dashboards[0]
        } catch (error) {
          console.warn('Failed to load from API, using local storage:', error)
        }
      }

      // If still no dashboard, create a default one
      if (!defaultDashboard) {
        defaultDashboard = {
          id: 'default-dashboard',
          name: 'Default Dashboard',
          layout: [],
          widgets: [],
          schema_version: '1.0.0',
          is_default: true
        }
      }

      setDashboard(defaultDashboard)
    } catch (error) {
      console.error('Failed to load dashboard:', error)
    } finally {
      setLoading(false)
    }
  }

  const onLayoutChange = (layout: any) => {
    if (dashboard) {
      const updated = {
        ...dashboard,
        layout,
        updated_at: new Date().toISOString()
      }
      setDashboard(updated)
      // Save to storage
      storage.storage.saveDashboard(updated).catch(console.error)
    }
  }

  if (loading) {
    return <div className="dashboard-loading">Loading dashboard...</div>
  }

  if (!dashboard) {
    return <div className="dashboard-error">No dashboard available</div>
  }

  return (
    <div className="dashboard-page">
      <div className="dashboard-header">
        <h2>{dashboard.name}</h2>
        <div className="dashboard-actions">
          <a href="/dashboard/editor" className="btn btn-secondary">
            Edit Dashboard
          </a>
        </div>
      </div>

      <div className="dashboard-content">
        {dashboard.widgets && dashboard.widgets.length > 0 ? (
          <ResponsiveGridLayout
            className="layout"
            layouts={{ lg: dashboard.layout || [] }}
            breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
            cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
            rowHeight={100}
            onLayoutChange={onLayoutChange}
            isDraggable={true}
            isResizable={true}
          >
            {dashboard.widgets.map((widget: any) => (
              <div key={widget.id} className="dashboard-widget">
                <div className="widget-header">
                  <h4>{widget.title}</h4>
                  <span className="widget-type">{widget.type}</span>
                </div>
                <div className="widget-content">
                  {renderWidget(widget)}
                </div>
              </div>
            ))}
          </ResponsiveGridLayout>
        ) : (
          <div className="dashboard-empty">
            <p>No widgets configured. Click "Edit Dashboard" to add widgets.</p>
          </div>
        )}
      </div>
    </div>
  )
}

const renderWidget = (widget: any) => {
  switch (widget.type) {
    case 'metric':
      return <div className="widget-metric">Metric: {widget.title}</div>
    case 'chart':
      return <div className="widget-chart">Chart: {widget.title}</div>
    case 'table':
      return <div className="widget-table">Table: {widget.title}</div>
    case 'alert':
      return <div className="widget-alert">Alerts: {widget.title}</div>
    default:
      return <div className="widget-placeholder">{widget.title}</div>
  }
}

export default Dashboard

