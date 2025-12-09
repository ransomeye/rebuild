# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/installer/build_installer.ps1
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Script to generate MSI using WiX Toolset - generates .wxs file programmatically and builds MSI

#Requires -RunAsAdministrator

param(
    [Parameter(Mandatory=$false)]
    [string]$SourcePath = "..\",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputPath = ".\RansomEyeAgent.msi",
    
    [Parameter(Mandatory=$false)]
    [string]$Version = "1.0.0",
    
    [Parameter(Mandatory=$false)]
    [string]$ProductName = "RansomEye Security Agent"
)

$ErrorActionPreference = "Stop"

# Check for WiX Toolset
$candlePath = Get-Command candle.exe -ErrorAction SilentlyContinue
$lightPath = Get-Command light.exe -ErrorAction SilentlyContinue

if (-not $candlePath -or -not $lightPath) {
    Write-Host "WiX Toolset not found. Please install WiX Toolset from https://wixtoolset.org/"
    Write-Host "Or add WiX binaries to PATH"
    exit 1
}

function New-WiXSourceFile {
    param([string]$SourceDir, [string]$OutputFile, [string]$Version, [string]$ProductName)
    
    Write-Host "Generating WiX source file..."
    
    $wxsContent = @"
<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
    <Product Id="*" Name="$ProductName" Language="1033" Version="$Version" Manufacturer="RansomEye.Tech" UpgradeCode="B8F5B8F5-B8F5-B8F5-B8F5-B8F5B8F5B8F5">
        <Package InstallerVersion="200" Compressed="yes" InstallScope="perMachine" />
        
        <MajorUpgrade DowngradeErrorMessage="A newer version of [ProductName] is already installed." />
        
        <MediaTemplate />
        
        <Feature Id="ProductFeature" Title="RansomEye Agent" Level="1">
            <ComponentGroupRef Id="ProductComponents" />
        </Feature>
        
        <Directory Id="TARGETDIR" Name="SourceDir">
            <Directory Id="ProgramFilesFolder">
                <Directory Id="INSTALLFOLDER" Name="RansomEye\Agent">
                    <Component Id="AgentFiles" Guid="A1B2C3D4-E5F6-7890-ABCD-EF1234567890">
                        <File Id="AgentService" Source="$SourceDir\windows_service\ransomeye_agent_service.py" KeyPath="yes" />
                        <File Id="AgentMain" Source="$SourceDir\engine\agent_main.py" />
                        <File Id="CollectorETW" Source="$SourceDir\engine\collector_etw.py" />
                        <File Id="Detector" Source="$SourceDir\engine\detector.py" />
                        <File Id="Persistence" Source="$SourceDir\engine\persistence.py" />
                        <File Id="AgentClient" Source="$SourceDir\transport\agent_client.py" />
                        <File Id="Heartbeat" Source="$SourceDir\transport\heartbeat.py" />
                        <File Id="Uploader" Source="$SourceDir\transport\uploader.py" />
                        <File Id="Inferencer" Source="$SourceDir\models\inferencer.py" />
                        <File Id="SHAPSupport" Source="$SourceDir\models\shap_support.py" />
                        <File Id="ModelRegistry" Source="$SourceDir\models\model_registry.py" />
                        <File Id="KeyManager" Source="$SourceDir\security\key_manager.py" />
                        <File Id="ConfigValidator" Source="$SourceDir\security\config_validator.py" />
                    </Component>
                </Directory>
            </Directory>
            <Directory Id="ProgramDataFolder">
                <Directory Id="ProgramDataRansomEye" Name="RansomEye">
                    <Directory Id="ProgramDataAgent" Name="Agent">
                        <Component Id="DataDirectories" Guid="B2C3D4E5-F6A7-8901-BCDE-F23456789012">
                            <CreateFolder>
                                <Permission User="Everyone" GenericAll="yes" />
                            </CreateFolder>
                        </Component>
                    </Directory>
                </Directory>
            </Directory>
        </Directory>
        
        <ComponentGroup Id="ProductComponents" Directory="INSTALLFOLDER">
            <Component Id="AgentService" Guid="C3D4E5F6-A7B8-9012-CDEF-345678901234">
                <File Source="$SourceDir\windows_service\ransomeye_agent_service.py" />
            </Component>
        </ComponentGroup>
        
        <CustomAction Id="InstallService" Directory="INSTALLFOLDER" Execute="deferred" Impersonate="no"
                      ExeCommand="python.exe ransomeye_agent_service.py install" Return="check" />
        
        <CustomAction Id="StartService" Directory="INSTALLFOLDER" Execute="deferred" Impersonate="no"
                      ExeCommand="net start RansomEyeAgent" Return="check" />
        
        <CustomAction Id="StopService" Directory="INSTALLFOLDER" Execute="deferred" Impersonate="no"
                      ExeCommand="net stop RansomEyeAgent" Return="ignore" />
        
        <CustomAction Id="UninstallService" Directory="INSTALLFOLDER" Execute="deferred" Impersonate="no"
                      ExeCommand="python.exe ransomeye_agent_service.py remove" Return="ignore" />
        
        <InstallExecuteSequence>
            <Custom Action="InstallService" After="InstallFiles">NOT REMOVE</Custom>
            <Custom Action="StartService" After="InstallService">NOT REMOVE</Custom>
            <Custom Action="StopService" Before="RemoveFiles">REMOVE</Custom>
            <Custom Action="UninstallService" After="StopService">REMOVE</Custom>
        </InstallExecuteSequence>
    </Product>
</Wix>
"@
    
    Set-Content -Path $OutputFile -Value $wxsContent -Encoding UTF8
    Write-Host "WiX source file created: $OutputFile"
}

function Build-MSI {
    param([string]$WxsFile, [string]$OutputFile)
    
    Write-Host "Building MSI installer..."
    
    $wixobjFile = $WxsFile -replace '\.wxs$', '.wixobj'
    
    # Compile
    Write-Host "Compiling WiX source..."
    & candle.exe -out $wixobjFile $WxsFile
    if ($LASTEXITCODE -ne 0) {
        throw "WiX compilation failed"
    }
    
    # Link
    Write-Host "Linking MSI..."
    & light.exe -out $OutputFile $wixobjFile -ext WixUtilExtension
    if ($LASTEXITCODE -ne 0) {
        throw "WiX linking failed"
    }
    
    # Cleanup
    Remove-Item -Path $wixobjFile -Force -ErrorAction SilentlyContinue
    
    Write-Host "MSI installer created: $OutputFile"
}

# Main
try {
    $wxsFile = Join-Path $env:TEMP "RansomEyeAgent.wxs"
    
    # Generate WiX source
    New-WiXSourceFile -SourceDir (Resolve-Path $SourcePath).Path -OutputFile $wxsFile -Version $Version -ProductName $ProductName
    
    # Build MSI
    Build-MSI -WxsFile $wxsFile -OutputFile (Resolve-Path $OutputPath).Path
    
    # Cleanup
    Remove-Item -Path $wxsFile -Force -ErrorAction SilentlyContinue
    
    Write-Host "Installer build completed successfully"
    exit 0
    
} catch {
    Write-Host "Error building installer: $_"
    exit 1
}

