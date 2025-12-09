# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/updater/apply_update.ps1
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: PowerShell atomic update with rollback - stops service, snapshots binaries, extracts new files, restarts service, and restores on failure

#Requires -RunAsAdministrator

param(
    [Parameter(Mandatory=$true)]
    [string]$UpdateBundlePath,
    
    [Parameter(Mandatory=$false)]
    [string]$UpdateKeyPath = ""
)

$ErrorActionPreference = "Stop"
$ServiceName = "RansomEyeAgent"
$InstallPath = "$env:ProgramFiles\RansomEye\Agent"
$RollbackPath = "$env:ProgramData\RansomEye\rollback"
$LogPath = "$env:ProgramData\RansomEye\logs\update.log"

# Ensure log directory exists
$LogDir = Split-Path -Parent $LogPath
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] $Message"
    Write-Host $LogMessage
    Add-Content -Path $LogPath -Value $LogMessage
}

function Test-ServiceExists {
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    return $null -ne $service
}

function Stop-AgentService {
    Write-Log "Stopping $ServiceName service..."
    if (Test-ServiceExists) {
        $service = Get-Service -Name $ServiceName
        if ($service.Status -eq "Running") {
            Stop-Service -Name $ServiceName -Force
            $service.WaitForStatus("Stopped", (New-TimeSpan -Seconds 30))
            Write-Log "Service stopped successfully"
        } else {
            Write-Log "Service already stopped"
        }
    } else {
        Write-Log "Service does not exist, skipping stop"
    }
}

function Start-AgentService {
    Write-Log "Starting $ServiceName service..."
    if (Test-ServiceExists) {
        $service = Get-Service -Name $ServiceName
        if ($service.Status -ne "Running") {
            Start-Service -Name $ServiceName
            $service.WaitForStatus("Running", (New-TimeSpan -Seconds 30))
            Write-Log "Service started successfully"
            return $true
        } else {
            Write-Log "Service already running"
            return $true
        }
    } else {
        Write-Log "Service does not exist, cannot start"
        return $false
    }
}

function Create-RollbackSnapshot {
    Write-Log "Creating rollback snapshot..."
    if (Test-Path $RollbackPath) {
        Remove-Item -Path $RollbackPath -Recurse -Force
    }
    New-Item -ItemType Directory -Path $RollbackPath -Force | Out-Null
    
    if (Test-Path $InstallPath) {
        Copy-Item -Path "$InstallPath\*" -Destination $RollbackPath -Recurse -Force
        Write-Log "Rollback snapshot created at $RollbackPath"
        return $true
    } else {
        Write-Log "Install path does not exist, no snapshot needed"
        return $false
    }
}

function Restore-Rollback {
    Write-Log "Restoring from rollback snapshot..."
    if (Test-Path $RollbackPath) {
        if (Test-Path $InstallPath) {
            Remove-Item -Path "$InstallPath\*" -Recurse -Force
        }
        Copy-Item -Path "$RollbackPath\*" -Destination $InstallPath -Recurse -Force
        Write-Log "Rollback restored successfully"
        return $true
    } else {
        Write-Log "No rollback snapshot found"
        return $false
    }
}

function Extract-UpdateBundle {
    param([string]$BundlePath, [string]$ExtractPath)
    
    Write-Log "Extracting update bundle..."
    
    # Check if it's a ZIP file
    if ($BundlePath -like "*.zip") {
        Expand-Archive -Path $BundlePath -DestinationPath $ExtractPath -Force
        Write-Log "Update bundle extracted"
        return $true
    } else {
        Write-Log "Unsupported bundle format: $BundlePath"
        return $false
    }
}

function Apply-UpdateFiles {
    param([string]$ExtractPath)
    
    Write-Log "Applying update files..."
    
    # Ensure install directory exists
    if (-not (Test-Path $InstallPath)) {
        New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
    }
    
    # Copy files from extract path to install path
    if (Test-Path $ExtractPath) {
        $files = Get-ChildItem -Path $ExtractPath -Recurse
        foreach ($file in $files) {
            $relativePath = $file.FullName.Substring($ExtractPath.Length + 1)
            $destPath = Join-Path $InstallPath $relativePath
            $destDir = Split-Path -Parent $destPath
            
            if (-not (Test-Path $destDir)) {
                New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            }
            
            Copy-Item -Path $file.FullName -Destination $destPath -Force
        }
        Write-Log "Update files applied"
        return $true
    } else {
        Write-Log "Extract path does not exist"
        return $false
    }
}

function Test-ServiceHealth {
    Write-Log "Testing service health..."
    Start-Sleep -Seconds 10
    
    if (Test-ServiceExists) {
        $service = Get-Service -Name $ServiceName
        if ($service.Status -eq "Running") {
            Write-Log "Service health check passed"
            return $true
        } else {
            Write-Log "Service health check failed: service not running"
            return $false
        }
    } else {
        Write-Log "Service health check failed: service does not exist"
        return $false
    }
}

# Main update process
try {
    Write-Log "Starting update process..."
    Write-Log "Update bundle: $UpdateBundlePath"
    
    # Get update key path from environment variable if not provided
    if ([string]::IsNullOrEmpty($UpdateKeyPath)) {
        $UpdateKeyPath = [System.Environment]::GetEnvironmentVariable("AGENT_UPDATE_KEY_PATH", "Machine")
        if ([string]::IsNullOrEmpty($UpdateKeyPath)) {
            $UpdateKeyPath = "$env:ProgramData\RansomEye\certs\update_key.pub"
            Write-Log "Using default update key path: $UpdateKeyPath"
        } else {
            Write-Log "Using update key from environment: $UpdateKeyPath"
        }
    }
    
    Write-Log "Update key: $UpdateKeyPath"
    
    # Verify signature (call verify script)
    $verifyScript = Join-Path $PSScriptRoot "verify_update.ps1"
    if (Test-Path $verifyScript) {
        Write-Log "Verifying update signature..."
        & $verifyScript -UpdateBundlePath $UpdateBundlePath -UpdateKeyPath $UpdateKeyPath
        if ($LASTEXITCODE -ne 0) {
            throw "Signature verification failed"
        }
        Write-Log "Signature verification passed"
    } else {
        Write-Log "Warning: verify_update.ps1 not found, skipping signature verification"
    }
    
    # Stop service
    Stop-AgentService
    
    # Create rollback snapshot
    $snapshotCreated = Create-RollbackSnapshot
    
    # Extract update bundle
    $tempExtractPath = Join-Path $env:TEMP "ransomeye_update_$(Get-Date -Format 'yyyyMMddHHmmss')"
    New-Item -ItemType Directory -Path $tempExtractPath -Force | Out-Null
    
    try {
        if (-not (Extract-UpdateBundle -BundlePath $UpdateBundlePath -ExtractPath $tempExtractPath)) {
            throw "Failed to extract update bundle"
        }
        
        # Apply update files
        if (-not (Apply-UpdateFiles -ExtractPath $tempExtractPath)) {
            throw "Failed to apply update files"
        }
        
        # Start service
        if (-not (Start-AgentService)) {
            throw "Failed to start service"
        }
        
        # Test service health
        if (-not (Test-ServiceHealth)) {
            throw "Service health check failed"
        }
        
        Write-Log "Update completed successfully"
        
        # Cleanup
        Remove-Item -Path $tempExtractPath -Recurse -Force -ErrorAction SilentlyContinue
        
        exit 0
        
    } catch {
        Write-Log "Update failed: $_"
        Write-Log "Attempting rollback..."
        
        # Restore rollback
        if ($snapshotCreated) {
            Restore-Rollback
            Start-AgentService | Out-Null
        }
        
        # Cleanup
        Remove-Item -Path $tempExtractPath -Recurse -Force -ErrorAction SilentlyContinue
        
        exit 1
    }
    
} catch {
    Write-Log "Fatal error: $_"
    exit 1
}

