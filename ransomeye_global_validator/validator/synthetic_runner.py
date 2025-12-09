# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/validator/synthetic_runner.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Orchestrates validation runs by triggering injector, waiting, calling verifier, and generating signed PDF

import os
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from .scenario_manager import ScenarioManager, ValidationScenario
from .injector import Injector
from .verifier import Verifier
from .pdf_signer import PDFSigner
from ..ml.validator_model import ValidatorModel
from ..ml.shap_support import SHAPSupport
from ..chain.manifest_builder import ManifestBuilder
from ..chain.manifest_signer import ManifestSigner
from ..storage.run_store import RunStore
from ..storage.audit_ledger import AuditLedger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SyntheticRunner:
    """Orchestrates complete validation runs."""
    
    def __init__(self):
        """Initialize synthetic runner with all components."""
        self.scenario_manager = ScenarioManager()
        self.injector = Injector()
        self.verifier = Verifier()
        self.pdf_signer = PDFSigner()
        self.validator_model = ValidatorModel()
        self.shap_support = SHAPSupport(self.validator_model)
        self.manifest_builder = ManifestBuilder()
        self.manifest_signer = ManifestSigner()
        self.run_store = RunStore()
        self.audit_ledger = AuditLedger()
        logger.info("Synthetic runner initialized")
    
    async def run_validation(self, scenario_type: str = "happy_path", 
                            scenario_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run a complete validation scenario.
        
        Args:
            scenario_type: Type of scenario to run
            scenario_config: Optional scenario configuration
            
        Returns:
            Complete validation run result
        """
        run_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        logger.info(f"Starting validation run: {run_id} (type: {scenario_type})")
        
        try:
            # Create scenario
            if scenario_type == "happy_path":
                scenario = self.scenario_manager.create_happy_path_scenario()
            elif scenario_type == "stress_test":
                alert_count = scenario_config.get('alert_count', 10) if scenario_config else 10
                scenario = self.scenario_manager.create_stress_test_scenario(alert_count)
            else:
                raise ValueError(f"Unknown scenario type: {scenario_type}")
            
            # Execute scenario steps
            scenario_results = []
            for step in scenario.steps:
                step_result = await self._execute_step(step, scenario)
                scenario_results.append(step_result)
            
            # Determine scenario status
            scenario_passed = all(r.get('success', False) for r in scenario_results)
            
            # Collect metrics for ML validation
            metrics = self._collect_metrics(scenario_results)
            
            # Run ML validator
            ml_result = self.validator_model.predict_health(metrics)
            
            # Generate SHAP explanation
            shap_result = self.shap_support.generate_explanation(metrics, run_id)
            ml_result["shap_explanation"] = shap_result
            
            # Build run data
            run_data = {
                "run_id": run_id,
                "start_time": start_time.isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "scenario_type": scenario_type,
                "scenario_id": scenario.scenario_id,
                "scenario_name": scenario.name,
                "summary": {
                    "total_scenarios": 1,
                    "passed_scenarios": 1 if scenario_passed else 0,
                    "failed_scenarios": 0 if scenario_passed else 1,
                    "ml_health_score": ml_result.get('health_score', 0.0),
                    "ml_is_healthy": ml_result.get('is_healthy', False)
                },
                "scenarios": [{
                    "name": scenario.name,
                    "status": "PASSED" if scenario_passed else "FAILED",
                    "steps": scenario_results
                }],
                "metrics": metrics,
                "ml_result": ml_result
            }
            
            # Generate PDF report
            pdf_path = self.run_store.get_pdf_path(run_id)
            self.pdf_signer.generate_pdf(run_data, pdf_path)
            run_data["pdf_path"] = pdf_path
            
            # Build and sign manifest
            manifest = self.manifest_builder.build_manifest(run_data)
            manifest_path = self.run_store.get_manifest_path(run_id)
            self.manifest_builder.save_manifest(manifest, manifest_path)
            signed_manifest_path = self.manifest_signer.sign_manifest(manifest_path)
            run_data["manifest_path"] = signed_manifest_path
            
            # Store run data
            self.run_store.store_run(run_id, run_data)
            
            # Log to audit ledger
            self.audit_ledger.log_validation_run(run_id, scenario_passed, run_data)
            
            # Fail-closed: exit with non-zero if validation failed
            if not scenario_passed:
                logger.error(f"Validation run {run_id} FAILED - exiting with error")
                raise Exception(f"Validation failed: {run_data}")
            
            logger.info(f"Validation run {run_id} completed successfully")
            return run_data
        
        except Exception as e:
            logger.error(f"Validation run {run_id} failed: {e}", exc_info=True)
            
            # Log failure to audit ledger
            self.audit_ledger.log_validation_run(run_id, False, {"error": str(e)})
            
            # Fail-closed: re-raise exception
            raise
    
    async def _execute_step(self, step, scenario: ValidationScenario) -> Dict[str, Any]:
        """
        Execute a single validation step.
        
        Args:
            step: Step to execute
            scenario: Parent scenario
            
        Returns:
            Step execution result
        """
        step_start = datetime.utcnow()
        logger.info(f"Executing step: {step.name}")
        
        try:
            if step.step_id == "step_1":
                # Inject alert
                alert_data = scenario.synthetic_data.get("alert")
                result = await self.injector.inject_alert(alert_data)
                
                if result.get("success"):
                    scenario.synthetic_data["alert_id"] = result.get("alert_id")
                    scenario.synthetic_data["expected_incident_id"] = str(uuid.uuid4())  # Will be set by KillChain
                
                return {
                    "step_id": step.step_id,
                    "name": step.name,
                    "status": "PASSED" if result.get("success") else "FAILED",
                    "success": result.get("success", False),
                    "latency_ms": result.get("latency_ms", 0),
                    "details": result.get("response", {}),
                    "error": result.get("error")
                }
            
            elif step.step_id == "step_2":
                # Poll KillChain for incident creation
                alert_id = scenario.synthetic_data.get("alert_id")
                if not alert_id:
                    return {
                        "step_id": step.step_id,
                        "name": step.name,
                        "status": "FAILED",
                        "success": False,
                        "error": "Alert ID not available from step 1"
                    }
                
                # Generate incident_id and trigger KillChain timeline build
                incident_id = scenario.synthetic_data.get("expected_incident_id")
                if not incident_id:
                    incident_id = str(uuid.uuid4())
                    scenario.synthetic_data["expected_incident_id"] = incident_id
                
                # Trigger KillChain to build timeline (this creates the incident)
                alert_data = scenario.synthetic_data.get("alert")
                try:
                    timeline_result = await self.injector.build_timeline(incident_id, [alert_data])
                    if timeline_result.get("success"):
                        # Update incident_id from response if available
                        response_incident_id = timeline_result.get("response", {}).get("incident_id")
                        if response_incident_id:
                            incident_id = response_incident_id
                            scenario.synthetic_data["expected_incident_id"] = incident_id
                except Exception as e:
                    logger.warning(f"KillChain timeline build failed, will poll anyway: {e}")
                
                # Poll KillChain DB for incident creation with exponential backoff
                incident_result = await self.verifier.verify_incident_created(
                    incident_id, 
                    max_wait_seconds=step.timeout_seconds
                )
                
                return {
                    "step_id": step.step_id,
                    "name": step.name,
                    "status": "PASSED" if incident_result.get("success") else "FAILED",
                    "success": incident_result.get("success", False),
                    "latency_ms": incident_result.get("wait_time_seconds", 0) * 1000,
                    "details": incident_result,
                    "error": incident_result.get("error")
                }
            
            elif step.step_id == "step_3":
                # Poll for evidence logging
                file_hash = scenario.synthetic_data.get("file_hash_sha256")
                incident_id = scenario.synthetic_data.get("expected_incident_id")
                
                if not file_hash:
                    return {
                        "step_id": step.step_id,
                        "name": step.name,
                        "status": "FAILED",
                        "success": False,
                        "error": "File hash not available"
                    }
                
                evidence_result = await self.verifier.verify_evidence_logged(
                    file_hash, 
                    incident_id=incident_id,
                    max_wait_seconds=step.timeout_seconds
                )
                
                if evidence_result.get("success"):
                    scenario.synthetic_data["expected_evidence_id"] = evidence_result.get("evidence_id")
                
                return {
                    "step_id": step.step_id,
                    "name": step.name,
                    "status": "PASSED" if evidence_result.get("success") else "FAILED",
                    "success": evidence_result.get("success", False),
                    "latency_ms": evidence_result.get("wait_time_seconds", 0) * 1000,
                    "details": evidence_result,
                    "error": evidence_result.get("error")
                }
            
            elif step.step_id == "step_4":
                # Verify chain integrity
                alert_id = scenario.synthetic_data.get("alert_id")
                incident_id = scenario.synthetic_data.get("expected_incident_id")
                evidence_id = scenario.synthetic_data.get("expected_evidence_id")
                
                chain_result = await self.verifier.verify_chain_integrity(
                    alert_id, 
                    incident_id, 
                    evidence_id
                )
                
                return {
                    "step_id": step.step_id,
                    "name": step.name,
                    "status": "PASSED" if chain_result.get("chain_complete") else "FAILED",
                    "success": chain_result.get("chain_complete", False),
                    "latency_ms": 0,
                    "details": chain_result,
                    "error": chain_result.get("error")
                }
            
            else:
                return {
                    "step_id": step.step_id,
                    "name": step.name,
                    "status": "UNKNOWN",
                    "success": False,
                    "error": f"Unknown step: {step.step_id}"
                }
        
        except Exception as e:
            logger.error(f"Step {step.step_id} failed: {e}")
            return {
                "step_id": step.step_id,
                "name": step.name,
                "status": "FAILED",
                "success": False,
                "error": str(e),
                "latency_ms": (datetime.utcnow() - step_start).total_seconds() * 1000
            }
    
    def _collect_metrics(self, scenario_results: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Collect metrics from scenario results for ML validation.
        
        Args:
            scenario_results: List of step results
            
        Returns:
            Metrics dictionary
        """
        latencies = [r.get("latency_ms", 0) for r in scenario_results if r.get("latency_ms")]
        errors = sum(1 for r in scenario_results if not r.get("success", False))
        
        return {
            "api_latency_avg": sum(latencies) / len(latencies) if latencies else 0.0,
            "api_latency_max": max(latencies) if latencies else 0.0,
            "error_count": float(errors),
            "queue_depth": 0.0,  # Would be collected from actual queue metrics
            "total_steps": float(len(scenario_results)),
            "success_rate": (len(scenario_results) - errors) / len(scenario_results) if scenario_results else 0.0
        }

