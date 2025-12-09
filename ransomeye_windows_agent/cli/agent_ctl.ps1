# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/cli/agent_ctl.ps1
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: PowerShell Admin CLI for agent management (Get-Status, Flush-Buffer, etc.)

#Requires -RunAsAdministrator

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("status", "start", "stop", "restart", "flush-buffer", "health", "config")]
    [string]$Action
)

$ServiceName = "RansomEyeAgent"
$BufferDir = "$env:ProgramData\RansomEye\buffer\pending"

function Get-AgentStatus {
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($null -eq $service) {
        Write-Host "Service not found: $ServiceName"
        return
    }
    
    Write-Host "Service Status: $($service.Status)"
    Write-Host "Display Name: $($service.DisplayName)"
    Write-Host "Start Type: $($service.StartType)"
    
    # Check buffer
    if (Test-Path $BufferDir) {
        $pendingFiles = (Get-ChildItem -Path $BufferDir -File).Count
        Write-Host "Pending Events: $pendingFiles"
    } else {
        Write-Host "Pending Events: 0 (buffer directory not found)"
    }
}

function Start-Agent {
    if (Test-ServiceExists) {
        Start-Service -Name $ServiceName
        Write-Host "Service started"
    } else {
        Write-Host "Service not found"
    }
}

function Stop-Agent {
    if (Test-ServiceExists) {
        Stop-Service -Name $ServiceName -Force
        Write-Host "Service stopped"
    } else {
        Write-Host "Service not found"
    }
}

function Restart-Agent {
    Stop-Agent
    Start-Sleep -Seconds 3
    Start-Agent
}

function Flush-Buffer {
    Write-Host "Flushing buffer..."
    if (Test-Path $BufferDir) {
        $files = Get-ChildItem -Path $BufferDir -File
        $count = $files.Count
        Remove-Item -Path "$BufferDir\*" -Force
        Write-Host "Flushed $count files from buffer"
    } else {
        Write-Host "Buffer directory not found"
    }
}

function Test-AgentHealth {
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($null -eq $service) {
        Write-Host "UNHEALTHY: Service not found"
        return $false
    }
    
    if ($service.Status -ne "Running") {
        Write-Host "UNHEALTHY: Service not running"
        return $false
    }
    
    Write-Host "HEALTHY: Service is running"
    return $true
}

function Get-AgentConfig {
    Write-Host "Agent Configuration:"
    Write-Host "==================="
    Write-Host "CORE_API_URL: $env:CORE_API_URL"
    Write-Host "AGENT_CERT_PATH: $env:AGENT_CERT_PATH"
    Write-Host "AGENT_KEY_PATH: $env:AGENT_KEY_PATH"
    Write-Host "BUFFER_DIR: $env:BUFFER_DIR"
    Write-Host "MODEL_PATH: $env:MODEL_PATH"
    Write-Host "HEARTBEAT_INTERVAL_SEC: $env:HEARTBEAT_INTERVAL_SEC"
    Write-Host "AGENT_METRICS_PORT: $env:AGENT_METRICS_PORT"
    Write-Host "AGENT_UPDATE_KEY_PATH: $env:AGENT_UPDATE_KEY_PATH"
}

function Test-ServiceExists {
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    return $null -ne $service
}

# Main
switch ($Action) {
    "status" { Get-AgentStatus }
    "start" { Start-Agent }
    "stop" { Stop-Agent }
    "restart" { Restart-Agent }
    "flush-buffer" { Flush-Buffer }
    "health" { Test-AgentHealth }
    "config" { Get-AgentConfig }
    default { Write-Host "Unknown action: $Action" }
}

