// Path and File Name : /home/ransomeye/rebuild/ransomeye_ui/app/src/services/storage.ts
// Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
// Details of functionality of this file: Dexie.js IndexedDB storage implementation for offline-first architecture

import Dexie, { Table } from 'dexie'

// Define interfaces for stored data
export interface AlertRecord {
  id: string
  timestamp: string
  alert_type: string
  severity: string
  source: string
  title: string
  description?: string
  status: string
  raw_data?: any
  created_at: string
  updated_at: string
  synced_at: number // Timestamp when synced from API
}

export interface DashboardRecord {
  id: string
  name: string
  description?: string
  layout: any // React Grid Layout configuration
  widgets: any[] // Widget configurations
  schema_version: string
  created_at: string
  updated_at: string
  is_default: boolean
}

export interface ModelRecord {
  model_id: number
  name: string
  version: string
  status: string
  sha256: string
  file_path: string
  metadata_json?: string
  uploaded_at: string
  activated_at?: string
  synced_at: number
}

// Dexie database class
class RansomEyeDB extends Dexie {
  alerts!: Table<AlertRecord>
  dashboards!: Table<DashboardRecord>
  models!: Table<ModelRecord>

  constructor() {
    super('RansomEyeDB')
    
    this.version(1).stores({
      alerts: 'id, timestamp, severity, status, created_at, synced_at',
      dashboards: 'id, name, is_default, updated_at',
      models: 'model_id, name, version, status, sha256, synced_at'
    })
  }
}

// Create database instance
const db = new RansomEyeDB()

// Storage service class
class StorageService {
  // Alert operations
  async getAlerts(limit: number = 100): Promise<AlertRecord[]> {
    return await db.alerts
      .orderBy('created_at')
      .reverse()
      .limit(limit)
      .toArray()
  }

  async getAlertById(id: string): Promise<AlertRecord | undefined> {
    return await db.alerts.get(id)
  }

  async saveAlert(alert: AlertRecord): Promise<void> {
    alert.synced_at = Date.now()
    await db.alerts.put(alert)
  }

  async saveAlerts(alerts: AlertRecord[]): Promise<void> {
    const now = Date.now()
    const alertsWithSync = alerts.map(alert => ({
      ...alert,
      synced_at: now
    }))
    await db.alerts.bulkPut(alertsWithSync)
  }

  async deleteAlert(id: string): Promise<void> {
    await db.alerts.delete(id)
  }

  async clearAlerts(): Promise<void> {
    await db.alerts.clear()
  }

  // Dashboard operations
  async getDashboards(): Promise<DashboardRecord[]> {
    return await db.dashboards.orderBy('updated_at').reverse().toArray()
  }

  async getDashboardById(id: string): Promise<DashboardRecord | undefined> {
    return await db.dashboards.get(id)
  }

  async getDefaultDashboard(): Promise<DashboardRecord | undefined> {
    return await db.dashboards.where('is_default').equals(1).first()
  }

  async saveDashboard(dashboard: DashboardRecord): Promise<void> {
    await db.dashboards.put(dashboard)
  }

  async deleteDashboard(id: string): Promise<void> {
    await db.dashboards.delete(id)
  }

  // Model operations
  async getModels(): Promise<ModelRecord[]> {
    return await db.models.orderBy('synced_at').reverse().toArray()
  }

  async getModelById(modelId: number): Promise<ModelRecord | undefined> {
    return await db.models.get(modelId)
  }

  async saveModel(model: ModelRecord): Promise<void> {
    model.synced_at = Date.now()
    await db.models.put(model)
  }

  async saveModels(models: ModelRecord[]): Promise<void> {
    const now = Date.now()
    const modelsWithSync = models.map(model => ({
      ...model,
      synced_at: now
    }))
    await db.models.bulkPut(modelsWithSync)
  }

  async clearModels(): Promise<void> {
    await db.models.clear()
  }

  // Utility operations
  async getStorageStats(): Promise<{
    alerts: number
    dashboards: number
    models: number
    totalSize: number
  }> {
    const [alerts, dashboards, models] = await Promise.all([
      db.alerts.count(),
      db.dashboards.count(),
      db.models.count()
    ])

    // Estimate storage size (rough calculation)
    const totalSize = (alerts + dashboards + models) * 1024 // Rough estimate

    return {
      alerts,
      dashboards,
      models,
      totalSize
    }
  }

  async clearAll(): Promise<void> {
    await Promise.all([
      db.alerts.clear(),
      db.dashboards.clear(),
      db.models.clear()
    ])
  }
}

export const storageService = new StorageService()
export default db

