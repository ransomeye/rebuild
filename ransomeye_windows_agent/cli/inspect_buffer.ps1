# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/cli/inspect_buffer.ps1
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Debug tool to inspect buffer contents and event files

param(
    [Parameter(Mandatory=$false)]
    [int]$Limit = 10,
    
    [Parameter(Mandatory=$false)]
    [string]$BufferDir = "$env:ProgramData\RansomEye\buffer\pending"
)

function Inspect-Buffer {
    param([string]$Path, [int]$Limit)
    
    if (-not (Test-Path $Path)) {
        Write-Host "Buffer directory not found: $Path"
        return
    }
    
    $files = Get-ChildItem -Path $Path -File -Filter "*.json" | Sort-Object LastWriteTime -Descending | Select-Object -First $Limit
    
    Write-Host "Buffer Inspection: $Path"
    Write-Host "==================="
    Write-Host "Total files: $((Get-ChildItem -Path $Path -File).Count)"
    Write-Host "Showing: $($files.Count)"
    Write-Host ""
    
    foreach ($file in $files) {
        Write-Host "File: $($file.Name)"
        Write-Host "Size: $($file.Length) bytes"
        Write-Host "Modified: $($file.LastWriteTime)"
        
        try {
            $content = Get-Content -Path $file.FullName -Raw | ConvertFrom-Json
            Write-Host "Timestamp: $($content.timestamp)"
            Write-Host "Hostname: $($content.hostname)"
            if ($content.detection) {
                Write-Host "Threat Detected: $($content.detection.threat_detected)"
                Write-Host "Threat Type: $($content.detection.threat_type)"
            }
        } catch {
            Write-Host "Error reading file: $_"
        }
        
        Write-Host "---"
    }
}

Inspect-Buffer -Path $BufferDir -Limit $Limit

