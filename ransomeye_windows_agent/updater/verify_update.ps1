# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/updater/verify_update.ps1
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Verifies digital signature of update bundle using Get-AuthenticodeSignature or GPG wrapper

#Requires -RunAsAdministrator

param(
    [Parameter(Mandatory=$true)]
    [string]$UpdateBundlePath,
    
    [Parameter(Mandatory=$false)]
    [string]$UpdateKeyPath = ""
)

$ErrorActionPreference = "Stop"

function Test-AuthenticodeSignature {
    param([string]$FilePath)
    
    Write-Host "Checking Authenticode signature for: $FilePath"
    
    $signature = Get-AuthenticodeSignature -FilePath $FilePath
    
    if ($signature.Status -eq "Valid") {
        Write-Host "Authenticode signature is valid"
        Write-Host "Signer: $($signature.SignerCertificate.Subject)"
        return $true
    } else {
        Write-Host "Authenticode signature status: $($signature.Status)"
        return $false
    }
}

function Test-GPGSignature {
    param([string]$FilePath, [string]$KeyPath)
    
    Write-Host "Checking GPG signature for: $FilePath"
    
    # Check if GPG is available
    $gpgPath = Get-Command gpg -ErrorAction SilentlyContinue
    if (-not $gpgPath) {
        Write-Host "GPG not found, skipping GPG verification"
        return $false
    }
    
    # Check for .sig file
    $sigPath = "$FilePath.sig"
    if (-not (Test-Path $sigPath)) {
        Write-Host "GPG signature file not found: $sigPath"
        return $false
    }
    
    # Import public key if needed
    $keyName = Split-Path -Leaf $KeyPath
    $importResult = & gpg --import $KeyPath 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Warning: Failed to import GPG key (may already be imported)"
    }
    
    # Verify signature
    $verifyResult = & gpg --verify $sigPath $FilePath 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "GPG signature is valid"
        return $true
    } else {
        Write-Host "GPG signature verification failed"
        Write-Host $verifyResult
        return $false
    }
}

function Test-FileHash {
    param([string]$FilePath, [string]$ExpectedHashPath)
    
    if (-not (Test-Path $ExpectedHashPath)) {
        Write-Host "Hash file not found: $ExpectedHashPath"
        return $false
    }
    
    $expectedHash = (Get-Content $ExpectedHashPath -Raw).Trim()
    $actualHash = (Get-FileHash -Path $FilePath -Algorithm SHA256).Hash
    
    if ($actualHash -eq $expectedHash) {
        Write-Host "File hash matches"
        return $true
    } else {
        Write-Host "File hash mismatch"
        Write-Host "Expected: $expectedHash"
        Write-Host "Actual: $actualHash"
        return $false
    }
}

# Main verification
try {
    Write-Host "Verifying update bundle: $UpdateBundlePath"
    
    if (-not (Test-Path $UpdateBundlePath)) {
        throw "Update bundle not found: $UpdateBundlePath"
    }
    
    # Get update key path from environment variable if not provided
    if ([string]::IsNullOrEmpty($UpdateKeyPath)) {
        $UpdateKeyPath = [System.Environment]::GetEnvironmentVariable("AGENT_UPDATE_KEY_PATH", "Machine")
        if ([string]::IsNullOrEmpty($UpdateKeyPath)) {
            $UpdateKeyPath = "$env:ProgramData\RansomEye\certs\update_key.pub"
            Write-Host "Using default update key path: $UpdateKeyPath"
        } else {
            Write-Host "Using update key from environment: $UpdateKeyPath"
        }
    }
    
    $verified = $false
    
    # Try Authenticode signature first
    if (Test-AuthenticodeSignature -FilePath $UpdateBundlePath) {
        $verified = $true
    }
    
    # Try GPG signature
    if (-not $verified -and (Test-Path $UpdateKeyPath)) {
        if (Test-GPGSignature -FilePath $UpdateBundlePath -KeyPath $UpdateKeyPath) {
            $verified = $true
        }
    }
    
    # Try hash verification as fallback
    if (-not $verified) {
        $hashPath = "$UpdateBundlePath.sha256"
        if (Test-FileHash -FilePath $UpdateBundlePath -ExpectedHashPath $hashPath) {
            Write-Host "Hash verification passed (signature verification unavailable)"
            $verified = $true
        }
    }
    
    if (-not $verified) {
        throw "Update bundle verification failed - no valid signature or hash found"
    }
    
    Write-Host "Update bundle verification passed"
    exit 0
    
} catch {
    Write-Host "Verification error: $_"
    exit 1
}

