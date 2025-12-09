# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/security/key_manager.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Checks NTFS permissions (ACLs) on key files and validates certificate/key security

import os
from pathlib import Path
from typing import List, Dict, Any
import logging

try:
    import win32security
    import ntsecuritycon
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KeyManager:
    """Manages security keys and validates NTFS permissions."""
    
    def __init__(self):
        """Initialize key manager."""
        cert_base = os.path.join(
            os.environ.get('PROGRAMDATA', 'C:\\ProgramData'),
            'RansomEye',
            'certs'
        )
        
        self.cert_path = Path(os.environ.get('AGENT_CERT_PATH', os.path.join(cert_base, 'agent.crt')))
        self.key_path = Path(os.environ.get('AGENT_KEY_PATH', os.path.join(cert_base, 'agent.key')))
        self.ca_cert_path = Path(os.environ.get('CA_CERT_PATH', os.path.join(cert_base, 'ca.crt')))
        
        logger.info("Key manager initialized")
    
    def check_permissions(self) -> Dict[str, Any]:
        """
        Check NTFS permissions on key files.
        
        Returns:
            Dictionary with permission check results
        """
        results = {
            "cert_path": str(self.cert_path),
            "key_path": str(self.key_path),
            "ca_cert_path": str(self.ca_cert_path),
            "checks": {}
        }
        
        if not WIN32_AVAILABLE:
            logger.warning("win32security not available, skipping permission checks")
            results["checks"]["win32_available"] = False
            return results
        
        results["checks"]["win32_available"] = True
        
        # Check certificate permissions
        if self.cert_path.exists():
            results["checks"]["cert_permissions"] = self._check_file_permissions(self.cert_path)
        else:
            results["checks"]["cert_permissions"] = {"exists": False}
        
        # Check key permissions (should be more restrictive)
        if self.key_path.exists():
            results["checks"]["key_permissions"] = self._check_file_permissions(self.key_path)
        else:
            results["checks"]["key_permissions"] = {"exists": False}
        
        # Check CA certificate permissions
        if self.ca_cert_path.exists():
            results["checks"]["ca_cert_permissions"] = self._check_file_permissions(self.ca_cert_path)
        else:
            results["checks"]["ca_cert_permissions"] = {"exists": False}
        
        return results
    
    def _check_file_permissions(self, file_path: Path) -> Dict[str, Any]:
        """
        Check NTFS permissions on a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Permission information dictionary
        """
        if not WIN32_AVAILABLE:
            return {"error": "win32security not available"}
        
        try:
            # Get security descriptor
            sd = win32security.GetFileSecurity(
                str(file_path),
                win32security.DACL_SECURITY_INFORMATION
            )
            
            dacl = sd.GetSecurityDescriptorDacl()
            
            # Get owner
            owner_sid = sd.GetSecurityDescriptorOwner()
            owner_name, _, _ = win32security.LookupAccountSid(None, owner_sid)
            
            # Analyze ACL
            acl_info = []
            if dacl:
                for i in range(dacl.GetAceCount()):
                    ace = dacl.GetAce(i)
                    ace_type, ace_flags, sid = ace[0], ace[1], ace[2]
                    
                    try:
                        account_name, domain, _ = win32security.LookupAccountSid(None, sid)
                        full_name = f"{domain}\\{account_name}" if domain else account_name
                    except:
                        full_name = str(sid)
                    
                    # Get access mask
                    access_mask = ace[3]
                    
                    acl_info.append({
                        "type": "ALLOW" if ace_type == win32security.ACCESS_ALLOWED_ACE_TYPE else "DENY",
                        "account": full_name,
                        "access": self._decode_access_mask(access_mask)
                    })
            
            return {
                "exists": True,
                "owner": owner_name,
                "acl": acl_info
            }
        
        except Exception as e:
            logger.error(f"Error checking permissions for {file_path}: {e}")
            return {"error": str(e)}
    
    def _decode_access_mask(self, access_mask: int) -> List[str]:
        """Decode Windows access mask to permission names."""
        permissions = []
        
        if access_mask & win32security.FILE_READ_DATA:
            permissions.append("READ")
        if access_mask & win32security.FILE_WRITE_DATA:
            permissions.append("WRITE")
        if access_mask & win32security.FILE_EXECUTE:
            permissions.append("EXECUTE")
        if access_mask & win32security.DELETE:
            permissions.append("DELETE")
        if access_mask & win32security.READ_CONTROL:
            permissions.append("READ_CONTROL")
        if access_mask & win32security.WRITE_DAC:
            permissions.append("WRITE_DAC")
        if access_mask & win32security.WRITE_OWNER:
            permissions.append("WRITE_OWNER")
        
        return permissions if permissions else ["UNKNOWN"]

