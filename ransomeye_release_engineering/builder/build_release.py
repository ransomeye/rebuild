# Path and File Name : /home/ransomeye/rebuild/ransomeye_release_engineering/builder/build_release.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Robust Release Builder with Real Signing

import os
import sys
import tarfile
import zipfile
import hashlib
import json
import subprocess
import shutil
# CRITICAL: Import both datetime class and timezone class
from datetime import datetime, timezone

ROOT_DIR = "/home/ransomeye/rebuild"
ARTIFACTS_DIR = os.path.join(ROOT_DIR, "release_artifacts")
SIGNING_KEY = os.path.join(ROOT_DIR, "keys/release_private.pem")

def run_governance_gate():
    print("======================================================================")
    print("STEP 1: Running Governance Gate Checks")
    print("======================================================================")
    gate_script = os.path.join(ROOT_DIR, "ransomeye_governance/gates/check_gates.py")
    
    try:
        subprocess.run([sys.executable, gate_script], check=True)
        print("\n✅ Governance Gate: PASSED\n")
    except subprocess.CalledProcessError:
        print("\n❌ Governance Gate: FAILED. Aborting Release.")
        sys.exit(1)

def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def sign_artifact(file_path):
    sig_path = file_path + ".sig"
    
    if os.path.exists(SIGNING_KEY):
        try:
            cmd = [
                "openssl", "dgst", "-sha256", "-sign", SIGNING_KEY,
                "-out", sig_path, file_path
            ]
            subprocess.run(cmd, check=True)
            print(f"  🔒 Signed: {os.path.basename(sig_path)}")
            return True
        except Exception as e:
            print(f"  ⚠️ Signing Failed: {e}")
            return False
    else:
        print(f"  ⚠️ Private Key not found at {SIGNING_KEY}. Skipping signature.")
        return False

def exclude_filter(tarinfo):
    name = tarinfo.name
    if "__pycache__" in name or ".venv" in name or ".git" in name or ".DS_Store" in name:
        return None
    return tarinfo

def build_artifact(name, contents, type="tar"):
    print(f"📦 Building {name} artifact...")
    output_filename = f"ransomeye-{name}.{type}" if type == "zip" else f"ransomeye-{name}.tar.gz"
    output_path = os.path.join(ARTIFACTS_DIR, output_filename)
    
    try:
        if type == "zip":
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for item in contents:
                    src_path = os.path.join(ROOT_DIR, item)
                    if os.path.isdir(src_path):
                        for root, _, files in os.walk(src_path):
                            for file in files:
                                if "__pycache__" in root or ".venv" in root:
                                    continue
                                file_path = os.path.join(root, file)
                                if os.path.exists(file_path):
                                    arcname = os.path.relpath(file_path, ROOT_DIR)
                                    zipf.write(file_path, arcname)
                    elif os.path.exists(src_path):
                        zipf.write(src_path, item)
        else:
            with tarfile.open(output_path, "w:gz") as tar:
                for item in contents:
                    src_path = os.path.join(ROOT_DIR, item)
                    if os.path.exists(src_path):
                        tar.add(src_path, arcname=item, filter=exclude_filter)
                    else:
                        print(f"  ⚠️ Warning: {item} not found, skipping.")

        file_hash = calculate_sha256(output_path)
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        print(f"  ✅ Created: {output_filename} ({size_mb:.2f} MB)")
        print(f"  ✅ SHA256: {file_hash}")
        
        sign_artifact(output_path)
        
        return {"filename": output_filename, "sha256": file_hash}

    except Exception as e:
        print(f"  ❌ Build Failed: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        sys.exit(1)

def main():
    if not os.path.exists(ARTIFACTS_DIR):
        os.makedirs(ARTIFACTS_DIR)
        
    run_governance_gate()
    
    print("======================================================================")
    print("STEP 2: Building Release Artifacts")
    print("======================================================================")
    
    # Correct Usage of timezone.utc
    manifest = {
        "version": os.environ.get("VERSION", "1.0.0-rc1"),
        "build_date": datetime.now(timezone.utc).isoformat(),
        "artifacts": []
    }
    
    # 1. Core Bundle
    core_content = [
        "ransomeye_core", "ransomeye_db_core", "ransomeye_ai_core", 
        "ransomeye_threat_intel", "ransomeye_killchain", "ransomeye_response", 
        "ransomeye_east_west_ml", "ransomeye_llm_summarizer", "ransomeye_ui", 
        "install.sh", "requirements.txt"
    ]
    manifest["artifacts"].append(build_artifact("core", core_content))
    
    # 2. Linux Agent
    manifest["artifacts"].append(build_artifact("linux_agent", ["ransomeye_linux_agent"]))
    
    # 3. Windows Agent
    manifest["artifacts"].append(build_artifact("windows_agent", ["ransomeye_windows_agent"], type="zip"))
    
    # 4. DPI Probe
    manifest["artifacts"].append(build_artifact("dpi_probe", ["ransomeye_dpi_probe"]))
    
    # Manifest
    manifest_path = os.path.join(ARTIFACTS_DIR, "release_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=4)
        
    print(f"\n📝 Manifest created: {manifest_path}")
    sign_artifact(manifest_path)
    
    print("\n======================================================================")
    print("BUILD SUCCESSFUL")
    print("======================================================================")

if __name__ == "__main__":
    main()
