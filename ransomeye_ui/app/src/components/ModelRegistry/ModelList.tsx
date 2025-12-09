// Path and File Name : /home/ransomeye/rebuild/ransomeye_ui/app/src/components/ModelRegistry/ModelList.tsx
// Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
// Details of functionality of this file: Model registry table view with retrain functionality

import React, { useState, useEffect } from 'react'
import { useApi } from '../../contexts/ApiContext'
import { ModelRecord } from '../../services/storage'
import './ModelList.css'

const ModelList: React.FC = () => {
  const { api, isOnline } = useApi()
  const [models, setModels] = useState<ModelRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retraining, setRetraining] = useState<number | null>(null)

  useEffect(() => {
    loadModels()
  }, [])

  const loadModels = async () => {
    try {
      setLoading(true)
      const modelList = await api.api.getModels()
      setModels(modelList)
      setError(null)
    } catch (err) {
      setError(`Failed to load models: ${(err as Error).message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleRetrain = async (modelId: number) => {
    if (!isOnline) {
      alert('Cannot retrain model: Backend API is offline')
      return
    }

    if (!confirm(`Are you sure you want to retrain model ${modelId}?`)) {
      return
    }

    try {
      setRetraining(modelId)
      await api.api.retrainModel(modelId)
      alert('Model retraining initiated successfully')
      // Reload models after a delay
      setTimeout(() => {
        loadModels()
      }, 2000)
    } catch (err) {
      alert(`Failed to retrain model: ${(err as Error).message}`)
    } finally {
      setRetraining(null)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return 'status-active'
      case 'inactive':
        return 'status-inactive'
      case 'deprecated':
        return 'status-deprecated'
      default:
        return 'status-unknown'
    }
  }

  if (loading) {
    return <div className="model-list-loading">Loading models...</div>
  }

  if (error) {
    return <div className="model-list-error">Error: {error}</div>
  }

  return (
    <div className="model-list">
      <div className="model-list-header">
        <h2>AI Model Registry</h2>
        <button onClick={loadModels} className="btn btn-secondary">
          Refresh
        </button>
      </div>

      <div className="model-table-container">
        <table className="model-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Version</th>
              <th>Status</th>
              <th>SHA256</th>
              <th>Uploaded</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {models.length === 0 ? (
              <tr>
                <td colSpan={7} className="empty-message">
                  No models found
                </td>
              </tr>
            ) : (
              models.map((model) => (
                <tr key={model.model_id}>
                  <td>{model.model_id}</td>
                  <td>{model.name}</td>
                  <td>{model.version}</td>
                  <td>
                    <span className={`status-badge ${getStatusColor(model.status)}`}>
                      {model.status}
                    </span>
                  </td>
                  <td className="sha256-cell">{model.sha256.substring(0, 16)}...</td>
                  <td>{new Date(model.uploaded_at).toLocaleDateString()}</td>
                  <td>
                    <button
                      onClick={() => handleRetrain(model.model_id)}
                      disabled={!isOnline || retraining === model.model_id}
                      className="btn btn-primary btn-sm"
                    >
                      {retraining === model.model_id ? 'Retraining...' : 'Retrain'}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {!isOnline && (
        <div className="offline-notice">
          ⚠️ Offline mode: Showing cached models. Retrain functionality unavailable.
        </div>
      )}
    </div>
  )
}

export default ModelList

