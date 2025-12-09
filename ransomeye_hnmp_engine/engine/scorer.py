# Path and File Name : /home/ransomeye/rebuild/ransomeye_hnmp_engine/engine/scorer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Calculates 0-100 health score using base score from rules and ML risk multiplier

import os
from typing import Dict, Any, List
from ..ml.risk_model import RiskModel
from ..ml.shap_explainer import SHAPExplainer
from .compliance_evaluator import ComplianceEvaluator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthScorer:
    """
    Calculates health score (0-100) based on compliance results and ML risk prediction.
    """
    
    def __init__(self, risk_model: RiskModel = None, compliance_evaluator: ComplianceEvaluator = None):
        """
        Initialize health scorer.
        
        Args:
            risk_model: Risk model instance
            compliance_evaluator: Compliance evaluator instance
        """
        self.risk_model = risk_model or RiskModel()
        self.compliance_evaluator = compliance_evaluator or ComplianceEvaluator()
        self.shap_explainer = SHAPExplainer(self.risk_model.model, self.risk_model.scaler)
        
        # Default rule weights by severity
        self.rule_weights = {
            'critical': 10.0,
            'high': 5.0,
            'medium': 2.0,
            'low': 1.0
        }
    
    def calculate_base_score(self, results: List[Dict[str, Any]], rule_weights: Dict[str, float] = None) -> float:
        """
        Calculate base score from compliance results (before ML adjustment).
        Starts at 100 and deducts points for failures.
        
        Args:
            results: List of compliance evaluation results
            rule_weights: Dictionary mapping severity to weight, or None for defaults
            
        Returns:
            Base score (0.0 - 100.0)
        """
        if rule_weights is None:
            rule_weights = self.rule_weights
        
        base_score = 100.0
        
        for result in results:
            if not result['passed']:
                severity = result['severity']
                weight = rule_weights.get(severity, 1.0)
                
                # Deduct points based on severity weight
                base_score -= weight
                
                # Use custom weight from rule if available
                rule_weight = result.get('weight')
                if rule_weight is not None:
                    base_score += weight  # Undo default deduction
                    base_score -= rule_weight  # Apply custom weight
        
        # Clamp to [0, 100]
        return max(0.0, min(100.0, base_score))
    
    def calculate_health_score(self, host_data: Dict[str, Any], 
                              compliance_results: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Calculate complete health score with ML risk adjustment and SHAP explanation.
        
        Args:
            host_data: Host profile dictionary
            compliance_results: Pre-computed compliance results, or None to compute
            
        Returns:
            Dictionary with score, base_score, risk_factor, shap_explanation, etc.
        """
        # Get compliance results if not provided
        if compliance_results is None:
            profile = host_data.get('profile', host_data)
            compliance_results = self.compliance_evaluator.evaluate_all_rules(profile)
        
        # Calculate base score
        base_score = self.calculate_base_score(compliance_results)
        
        # Count failures by severity
        failed_counts = self.compliance_evaluator.get_failed_rules_by_severity(compliance_results)
        
        # Prepare data for risk model
        risk_input = host_data.copy()
        risk_input['num_failed_high'] = failed_counts['high']
        risk_input['num_failed_critical'] = failed_counts['critical']
        
        # Predict risk factor
        risk_factor = self.risk_model.predict(risk_input)
        
        # Adjust score based on risk factor
        # Higher risk reduces score more
        risk_adjustment = risk_factor * 20.0  # Max 20 points reduction
        final_score = base_score - risk_adjustment
        
        # Clamp to [0, 100]
        final_score = max(0.0, min(100.0, final_score))
        
        # Get SHAP explanation
        shap_explanation = self.shap_explainer.explain(risk_input, risk_factor)
        
        return {
            'score': float(final_score),
            'base_score': float(base_score),
            'risk_factor': float(risk_factor),
            'risk_adjustment': float(risk_adjustment),
            'failed_counts': failed_counts,
            'shap_explanation': shap_explanation,
            'compliance_results': compliance_results
        }

