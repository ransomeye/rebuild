# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/updater/build_update_bundle.ps1
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CI tool to package updates into signed bundles with version metadata

param(
    [Parameter(Mandatory=$true)]
    [string]$SourcePath,
    
    [Parameter(Mandatory=$true)]
    [string]$OutputPath,
    
    [Parameter(Mandatory=$true)]
    [string]$Version,
    
    [Parameter(Mandatory=$false)]
    [string]$SignKeyPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$SignCertPath = ""
)

$ErrorActionPreference = "Stop"

function New-UpdateBundle {
    param([string]$Source, [string]$Output, [string]$Version)
    
    Write-Host "Creating update bundle..."
    Write-Host "Source: $Source"
    Write-Host "Output: $Output"
    Write-Host "Version: $Version"
    
    # Create temporary directory
    $tempDir = Join-Path $env:TEMP "ransomeye_bundle_$(Get-Date -Format 'yyyyMMddHHmmss')"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    
    try {
        # Copy source files
        Copy-Item -Path "$Source\*" -Destination $tempDir -Recurse -Force
        
        # Create version file
        $versionFile = Join-Path $tempDir "VERSION.txt"
        Set-Content -Path $versionFile -Value $Version
        
        # Create manifest
        $manifest = @{
            version = $Version
            timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
            files = @()
        }
        
        $files = Get-ChildItem -Path $tempDir -Recurse -File
        foreach ($file in $files) {
            $relativePath = $file.FullName.Substring($tempDir.Length + 1)
            $hash = (Get-FileHash -Path $file.FullName -Algorithm SHA256).Hash
            $manifest.files += @{
                path = $relativePath
                hash = $hash
                size = $file.Length
            }
        }
        
        $manifestFile = Join-Path $tempDir "MANIFEST.json"
        $manifest | ConvertTo-Json -Depth 10 | Set-Content -Path $manifestFile
        
        # Create ZIP archive
        if (Test-Path $Output) {
            Remove-Item -Path $Output -Force
        }
        
        Compress-Archive -Path "$tempDir\*" -DestinationPath $Output -Force
        Write-Host "Update bundle created: $Output"
        
        # Generate hash file
        $hashFile = "$Output.sha256"
        $bundleHash = (Get-FileHash -Path $Output -Algorithm SHA256).Hash
        Set-Content -Path $hashFile -Value $bundleHash
        Write-Host "Hash file created: $hashFile"
        
        # Sign if key provided
        if ($SignKeyPath -and (Test-Path $SignKeyPath)) {
            Write-Host "Signing update bundle..."
            # GPG signing
            $gpgPath = Get-Command gpg -ErrorAction SilentlyContinue
            if ($gpgPath) {
                & gpg --detach-sign --armor --output "$Output.sig" $Output
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "GPG signature created: $Output.sig"
                }
            }
        }
        
        # Authenticode signing if cert provided
        if ($SignCertPath -and (Test-Path $SignCertPath)) {
            Write-Host "Applying Authenticode signature..."
            $signtool = Get-Command signtool -ErrorAction SilentlyContinue
            if ($signtool) {
                & signtool sign /f $SignCertPath /p "" /t http://timestamp.digicert.com $Output
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "Authenticode signature applied"
                }
            }
        }
        
    } finally {
        # Cleanup
        Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Main
try {
    New-UpdateBundle -Source $SourcePath -Output $OutputPath -Version $Version
    Write-Host "Update bundle build completed successfully"
    exit 0
} catch {
    Write-Host "Error building update bundle: $_"
    exit 1
}

