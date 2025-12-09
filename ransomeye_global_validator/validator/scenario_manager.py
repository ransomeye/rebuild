# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/validator/scenario_manager.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Manages validation scenarios including Happy Path and synthetic data generation

import os
import uuid
import hashlib
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ScenarioStep:
    """Represents a single step in a validation scenario."""
    step_id: str
    name: str
    description: str
    expected_result: str
    timeout_seconds: int = 60
    retry_count: int = 3


@dataclass
class ValidationScenario:
    """Represents a complete validation scenario."""
    scenario_id: str
    name: str
    description: str
    steps: List[ScenarioStep]
    synthetic_data: Dict[str, Any]
    created_at: datetime


class ScenarioManager:
    """Manages validation scenarios and synthetic data generation."""
    
    def __init__(self):
        """Initialize scenario manager."""
        self.scenarios = {}
        logger.info("Scenario manager initialized")
    
    def generate_synthetic_alert(self) -> Dict[str, Any]:
        """
        Generate synthetic ransomware alert data.
        
        Returns:
            Synthetic alert payload
        """
        alert_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Generate random IP addresses
        source_ip = f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        target_ip = f"192.168.{random.randint(0, 255)}.{random.randint(1, 254)}"
        
        # Generate random file hash
        random_data = ''.join(random.choices(string.ascii_letters + string.digits, k=64))
        file_hash = hashlib.sha256(random_data.encode()).hexdigest()
        
        # Generate random file path
        file_path = f"/tmp/{''.join(random.choices(string.ascii_lowercase, k=12))}.encrypted"
        
        alert_data = {
            "source": f"endpoint_{random.randint(1000, 9999)}",
            "alert_type": "ransomware_encryption",
            "target": target_ip,
            "severity": random.choice(["high", "critical"]),
            "timestamp": timestamp,
            "metadata": {
                "file_path": file_path,
                "file_hash_sha256": file_hash,
                "encryption_extension": random.choice([".lockbit", ".ryuk", ".conti", ".maze"]),
                "process_name": random.choice(["encrypt.exe", "crypto.exe", "lock.exe"]),
                "source_ip": source_ip,
                "user_account": f"user{random.randint(1, 100)}",
                "detection_method": "behavioral_analysis",
                "confidence_score": round(random.uniform(0.85, 0.99), 2)
            }
        }
        
        logger.info(f"Generated synthetic alert: {alert_id}")
        return alert_data
    
    def create_happy_path_scenario(self) -> ValidationScenario:
        """
        Create the Happy Path validation scenario.
        
        Returns:
            Happy Path scenario
        """
        scenario_id = str(uuid.uuid4())
        synthetic_alert = self.generate_synthetic_alert()
        
        steps = [
            ScenarioStep(
                step_id="step_1",
                name="Inject Synthetic Ransomware Alert",
                description="Inject synthetic ransomware alert into Alert Engine API",
                expected_result="Alert ingested successfully with alert_id returned",
                timeout_seconds=30,
                retry_count=3
            ),
            ScenarioStep(
                step_id="step_2",
                name="Poll KillChain for Incident Creation",
                description="Verify that KillChain created an incident from the alert",
                expected_result="Incident found in KillChain with matching incident_id",
                timeout_seconds=60,
                retry_count=5
            ),
            ScenarioStep(
                step_id="step_3",
                name="Poll Forensic DB for Artifact Logging",
                description="Verify that forensic artifacts were logged in the database",
                expected_result="Evidence ledger entry found with matching SHA256 hash",
                timeout_seconds=90,
                retry_count=5
            ),
            ScenarioStep(
                step_id="step_4",
                name="Verify Chain Integrity",
                description="Verify that alert_id -> incident_id -> evidence_id chain is intact",
                expected_result="All relationships verified in database",
                timeout_seconds=30,
                retry_count=3
            )
        ]
        
        scenario = ValidationScenario(
            scenario_id=scenario_id,
            name="Happy Path - Ransomware Detection Chain",
            description="Validates the complete chain: Alert -> KillChain -> Forensic -> DB",
            steps=steps,
            synthetic_data={
                "alert": synthetic_alert,
                "expected_incident_id": None,  # Will be populated after step 1
                "expected_evidence_id": None,  # Will be populated after step 2
                "file_hash_sha256": synthetic_alert["metadata"]["file_hash_sha256"]
            },
            created_at=datetime.utcnow()
        )
        
        self.scenarios[scenario_id] = scenario
        logger.info(f"Created Happy Path scenario: {scenario_id}")
        return scenario
    
    def create_stress_test_scenario(self, alert_count: int = 10) -> ValidationScenario:
        """
        Create a stress test scenario with multiple alerts.
        
        Args:
            alert_count: Number of alerts to inject
            
        Returns:
            Stress test scenario
        """
        scenario_id = str(uuid.uuid4())
        synthetic_alerts = [self.generate_synthetic_alert() for _ in range(alert_count)]
        
        steps = [
            ScenarioStep(
                step_id="step_1",
                name="Inject Multiple Alerts",
                description=f"Inject {alert_count} synthetic alerts in rapid succession",
                expected_result=f"All {alert_count} alerts ingested successfully",
                timeout_seconds=120,
                retry_count=2
            ),
            ScenarioStep(
                step_id="step_2",
                name="Verify Processing Latency",
                description="Verify that all alerts are processed within acceptable latency",
                expected_result="Average processing latency < 500ms",
                timeout_seconds=180,
                retry_count=3
            )
        ]
        
        scenario = ValidationScenario(
            scenario_id=scenario_id,
            name=f"Stress Test - {alert_count} Alerts",
            description=f"Validates system performance under load with {alert_count} concurrent alerts",
            steps=steps,
            synthetic_data={
                "alerts": synthetic_alerts,
                "alert_count": alert_count
            },
            created_at=datetime.utcnow()
        )
        
        self.scenarios[scenario_id] = scenario
        logger.info(f"Created stress test scenario: {scenario_id} with {alert_count} alerts")
        return scenario
    
    def get_scenario(self, scenario_id: str) -> Optional[ValidationScenario]:
        """
        Get scenario by ID.
        
        Args:
            scenario_id: Scenario identifier
            
        Returns:
            Scenario or None if not found
        """
        return self.scenarios.get(scenario_id)
    
    def list_scenarios(self) -> List[Dict[str, Any]]:
        """
        List all scenarios.
        
        Returns:
            List of scenario metadata
        """
        return [
            {
                "scenario_id": scenario.scenario_id,
                "name": scenario.name,
                "description": scenario.description,
                "step_count": len(scenario.steps),
                "created_at": scenario.created_at.isoformat()
            }
            for scenario in self.scenarios.values()
        ]

