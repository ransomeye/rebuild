// Path and File Name : /home/ransomeye/rebuild/ransomeye_ui/app/src/pages/Alerts/AlertsView.tsx
// Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
// Details of functionality of this file: Alerts view page with filtering and offline support

import React, { useState, useEffect } from 'react'
import { useApi } from '../../contexts/ApiContext'
import { AlertRecord } from '../../services/storage'
import './AlertsView.css'

const AlertsView: React.FC = () => {
  const { api, isOnline } = useApi()
  const [alerts, setAlerts] = useState<AlertRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    severity: [] as string[],
    status: [] as string[],
    limit: 100
  })

  useEffect(() => {
    loadAlerts()
  }, [filters])

  const loadAlerts = async () => {
    try {
      setLoading(true)
      const alertList = await api.api.getAlerts(filters)
      setAlerts(alertList)
    } catch (error) {
      console.error('Failed to load alerts:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleStatusChange = async (alertId: string, newStatus: string) => {
    if (!isOnline) {
      alert('Cannot update alert: Backend API is offline')
      return
    }

    try {
      await api.api.updateAlertStatus(alertId, newStatus)
      // Reload alerts
      loadAlerts()
    } catch (error) {
      alert(`Failed to update alert: ${(error as Error).message}`)
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'severity-critical'
      case 'high':
        return 'severity-high'
      case 'medium':
        return 'severity-medium'
      case 'low':
        return 'severity-low'
      default:
        return 'severity-info'
    }
  }

  const toggleFilter = (type: 'severity' | 'status', value: string) => {
    setFilters(prev => {
      const current = prev[type] as string[]
      const updated = current.includes(value)
        ? current.filter(v => v !== value)
        : [...current, value]
      return { ...prev, [type]: updated }
    })
  }

  if (loading) {
    return <div className="alerts-loading">Loading alerts...</div>
  }

  return (
    <div className="alerts-view">
      <div className="alerts-header">
        <h2>Security Alerts</h2>
        <button onClick={loadAlerts} className="btn btn-secondary">
          Refresh
        </button>
      </div>

      <div className="alerts-filters">
        <div className="filter-group">
          <label>Severity:</label>
          {['critical', 'high', 'medium', 'low', 'info'].map(sev => (
            <label key={sev} className="filter-checkbox">
              <input
                type="checkbox"
                checked={filters.severity.includes(sev)}
                onChange={() => toggleFilter('severity', sev)}
              />
              {sev}
            </label>
          ))}
        </div>
        <div className="filter-group">
          <label>Status:</label>
          {['open', 'acknowledged', 'resolved', 'false_positive'].map(status => (
            <label key={status} className="filter-checkbox">
              <input
                type="checkbox"
                checked={filters.status.includes(status)}
                onChange={() => toggleFilter('status', status)}
              />
              {status}
            </label>
          ))}
        </div>
      </div>

      <div className="alerts-table-container">
        <table className="alerts-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Timestamp</th>
              <th>Type</th>
              <th>Severity</th>
              <th>Source</th>
              <th>Title</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {alerts.length === 0 ? (
              <tr>
                <td colSpan={8} className="empty-message">
                  No alerts found
                </td>
              </tr>
            ) : (
              alerts.map((alert) => (
                <tr key={alert.id}>
                  <td className="alert-id">{alert.id.substring(0, 8)}...</td>
                  <td>{new Date(alert.timestamp).toLocaleString()}</td>
                  <td>{alert.alert_type}</td>
                  <td>
                    <span className={`severity-badge ${getSeverityColor(alert.severity)}`}>
                      {alert.severity}
                    </span>
                  </td>
                  <td>{alert.source}</td>
                  <td className="alert-title">{alert.title}</td>
                  <td>{alert.status}</td>
                  <td>
                    <select
                      value={alert.status}
                      onChange={(e) => handleStatusChange(alert.id, e.target.value)}
                      disabled={!isOnline}
                      className="status-select"
                    >
                      <option value="open">Open</option>
                      <option value="acknowledged">Acknowledged</option>
                      <option value="resolved">Resolved</option>
                      <option value="false_positive">False Positive</option>
                    </select>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {!isOnline && (
        <div className="offline-notice">
          ⚠️ Offline mode: Showing cached alerts. Status updates unavailable.
        </div>
      )}
    </div>
  )
}

export default AlertsView

