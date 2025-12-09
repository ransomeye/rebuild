// Path and File Name : /home/ransomeye/rebuild/ransomeye_ui/app/src/services/api.ts
// Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
// Details of functionality of this file: Axios API wrapper with offline fallback to IndexedDB

import axios, { AxiosInstance, AxiosError } from 'axios'
import { storageService, AlertRecord, ModelRecord } from './storage'

// Get API URL from runtime config or environment
const getApiUrl = (): string => {
  const config = (window as any).__RUNTIME_CONFIG__
  return config?.API_URL || import.meta.env.VITE_API_URL || 'http://localhost:8080'
}

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: getApiUrl(),
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Network status tracking
let isOnline = navigator.onLine

window.addEventListener('online', () => {
  isOnline = true
  console.log('Network: Online')
})

window.addEventListener('offline', () => {
  isOnline = false
  console.log('Network: Offline - Switching to read-only mode')
})

// API Service class with offline fallback
class ApiService {
  private client: AxiosInstance

  constructor(client: AxiosInstance) {
    this.client = client
  }

  // Check if API is available
  async checkHealth(): Promise<boolean> {
    try {
      const response = await this.client.get('/api/v1/status', { timeout: 3000 })
      return response.status === 200
    } catch (error) {
      return false
    }
  }

  // Alert operations
  async getAlerts(params?: {
    severity?: string[]
    status?: string[]
    start_time?: string
    end_time?: string
    limit?: number
    offset?: number
  }): Promise<AlertRecord[]> {
    try {
      const response = await this.client.post('/query/alerts', params || {})
      const alerts = response.data.alerts || []
      
      // Sync to IndexedDB
      if (alerts.length > 0) {
        await storageService.saveAlerts(alerts)
      }
      
      return alerts
    } catch (error) {
      console.warn('API call failed, falling back to IndexedDB:', error)
      
      // Fallback to IndexedDB
      const limit = params?.limit || 100
      return await storageService.getAlerts(limit)
    }
  }

  async getAlertById(id: string): Promise<AlertRecord | null> {
    try {
      const response = await this.client.get(`/api/v1/alerts/${id}`)
      const alert = response.data
      
      // Sync to IndexedDB
      await storageService.saveAlert(alert)
      
      return alert
    } catch (error) {
      console.warn('API call failed, falling back to IndexedDB:', error)
      
      // Fallback to IndexedDB
      return (await storageService.getAlertById(id)) || null
    }
  }

  async updateAlertStatus(id: string, status: string): Promise<AlertRecord> {
    try {
      const response = await this.client.patch(`/api/v1/alerts/${id}`, { status })
      const alert = response.data
      
      // Update IndexedDB
      await storageService.saveAlert(alert)
      
      return alert
    } catch (error) {
      throw new Error(`Failed to update alert: ${(error as AxiosError).message}`)
    }
  }

  // Model operations
  async getModels(): Promise<ModelRecord[]> {
    try {
      const response = await this.client.get('/api/v1/models')
      const models = response.data.models || []
      
      // Sync to IndexedDB
      if (models.length > 0) {
        await storageService.saveModels(models)
      }
      
      return models
    } catch (error) {
      console.warn('API call failed, falling back to IndexedDB:', error)
      
      // Fallback to IndexedDB
      return await storageService.getModels()
    }
  }

  async getModelById(modelId: number): Promise<ModelRecord | null> {
    try {
      const response = await this.client.get(`/api/v1/models/${modelId}`)
      const model = response.data
      
      // Sync to IndexedDB
      await storageService.saveModel(model)
      
      return model
    } catch (error) {
      console.warn('API call failed, falling back to IndexedDB:', error)
      
      // Fallback to IndexedDB
      return (await storageService.getModelById(modelId)) || null
    }
  }

  async retrainModel(modelId: number): Promise<void> {
    try {
      await this.client.post(`/api/v1/models/${modelId}/retrain`)
    } catch (error) {
      throw new Error(`Failed to retrain model: ${(error as AxiosError).message}`)
    }
  }

  // Dashboard operations
  async getDashboards(): Promise<any[]> {
    try {
      const response = await this.client.get('/api/v1/dashboards')
      return response.data.dashboards || []
    } catch (error) {
      console.warn('API call failed, using local dashboards:', error)
      
      // Fallback to IndexedDB
      return await storageService.getDashboards()
    }
  }

  async saveDashboard(dashboard: any): Promise<void> {
    try {
      await this.client.post('/api/v1/dashboards', dashboard)
      
      // Also save locally
      await storageService.saveDashboard(dashboard)
    } catch (error) {
      // If API fails, still save locally
      await storageService.saveDashboard(dashboard)
      throw new Error(`Failed to save dashboard: ${(error as AxiosError).message}`)
    }
  }

  // Health check
  async getSystemStatus(): Promise<any> {
    try {
      const response = await this.client.get('/api/v1/status')
      return response.data
    } catch (error) {
      return {
        status: 'offline',
        message: 'Backend API is unavailable'
      }
    }
  }

  // Check if online
  isOnline(): boolean {
    return isOnline
  }
}

export const apiService = new ApiService(apiClient)
export default apiService

