// Path and File Name : /home/ransomeye/rebuild/ransomeye_ui/app/src/components/Editor/DashboardEditor.tsx
// Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
// Details of functionality of this file: Split-pane dashboard editor with JSON validation

import React, { useState, useEffect } from 'react'
import SplitPane from 'react-split-pane'
import Ajv from 'ajv'
import { useStorage } from '../../contexts/StorageContext'
import { useApi } from '../../contexts/ApiContext'
import dashboardSchema from '../../schema/dashboard.schema.json'
import './DashboardEditor.css'

const DashboardEditor: React.FC = () => {
  const { storage } = useStorage()
  const { api } = useApi()
  const [jsonText, setJsonText] = useState('')
  const [preview, setPreview] = useState<any>(null)
  const [errors, setErrors] = useState<string[]>([])
  const [isValid, setIsValid] = useState(false)
  const [saved, setSaved] = useState(false)

  const ajv = new Ajv()
  const validate = ajv.compile(dashboardSchema)

  useEffect(() => {
    // Load default dashboard or create new one
    loadDefaultDashboard()
  }, [])

  const loadDefaultDashboard = async () => {
    try {
      const defaultDashboard = await storage.storage.getDefaultDashboard()
      if (defaultDashboard) {
        setJsonText(JSON.stringify(defaultDashboard, null, 2))
        setPreview(defaultDashboard)
      } else {
        // Create new default dashboard
        const newDashboard = {
          id: `dashboard-${Date.now()}`,
          name: 'New Dashboard',
          description: '',
          layout: [],
          widgets: [],
          schema_version: '1.0.0',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          is_default: false
        }
        setJsonText(JSON.stringify(newDashboard, null, 2))
        setPreview(newDashboard)
      }
    } catch (error) {
      console.error('Failed to load dashboard:', error)
    }
  }

  const handleJsonChange = (value: string) => {
    setJsonText(value)
    setSaved(false)
    setErrors([])

    try {
      const parsed = JSON.parse(value)
      const valid = validate(parsed)

      if (valid) {
        setIsValid(true)
        setPreview(parsed)
      } else {
        setIsValid(false)
        const validationErrors = validate.errors?.map(err => 
          `${err.instancePath || 'root'}: ${err.message}`
        ) || []
        setErrors(validationErrors)
      }
    } catch (error) {
      setIsValid(false)
      setErrors([`JSON Parse Error: ${(error as Error).message}`])
    }
  }

  const handleSave = async () => {
    if (!isValid || !preview) {
      return
    }

    try {
      const dashboard = {
        ...preview,
        updated_at: new Date().toISOString()
      }

      // Save to IndexedDB
      await storage.storage.saveDashboard(dashboard)

      // Try to save to API (may fail if offline)
      try {
        await api.api.saveDashboard(dashboard)
      } catch (error) {
        console.warn('Failed to save to API, saved locally only:', error)
      }

      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (error) {
      setErrors([`Save failed: ${(error as Error).message}`])
    }
  }

  const handleExport = () => {
    if (!preview) return

    const dataStr = JSON.stringify(preview, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `dashboard-${preview.id}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="dashboard-editor">
      <div className="editor-header">
        <h2>Dashboard Editor</h2>
        <div className="editor-actions">
          <button 
            onClick={handleSave} 
            disabled={!isValid}
            className="btn btn-primary"
          >
            {saved ? '✓ Saved' : 'Save'}
          </button>
          <button onClick={handleExport} className="btn btn-secondary">
            Export JSON
          </button>
        </div>
      </div>

      <div className="editor-content">
        <SplitPane split="vertical" minSize={300} defaultSize="50%">
          <div className="editor-pane">
            <div className="editor-toolbar">
              <span className={isValid ? 'status valid' : 'status invalid'}>
                {isValid ? '✓ Valid' : '✗ Invalid'}
              </span>
            </div>
            <textarea
              className="json-editor"
              value={jsonText}
              onChange={(e) => handleJsonChange(e.target.value)}
              placeholder="Enter dashboard JSON..."
            />
            {errors.length > 0 && (
              <div className="error-list">
                <h4>Validation Errors:</h4>
                <ul>
                  {errors.map((error, idx) => (
                    <li key={idx}>{error}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="preview-pane">
            <div className="preview-header">
              <h3>Preview</h3>
            </div>
            <div className="preview-content">
              {preview ? (
                <div className="preview-dashboard">
                  <div className="preview-info">
                    <p><strong>Name:</strong> {preview.name}</p>
                    <p><strong>ID:</strong> {preview.id}</p>
                    <p><strong>Widgets:</strong> {preview.widgets?.length || 0}</p>
                    <p><strong>Layout Items:</strong> {preview.layout?.length || 0}</p>
                  </div>
                  {preview.widgets && preview.widgets.length > 0 && (
                    <div className="preview-widgets">
                      <h4>Widgets:</h4>
                      {preview.widgets.map((widget: any, idx: number) => (
                        <div key={idx} className="preview-widget">
                          <strong>{widget.type}</strong>: {widget.title || 'Untitled'}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="preview-empty">
                  Enter valid JSON to see preview
                </div>
              )}
            </div>
          </div>
        </SplitPane>
      </div>
    </div>
  )
}

export default DashboardEditor

