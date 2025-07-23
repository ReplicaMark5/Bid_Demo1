#!/usr/bin/env python3
"""
Best-Worst Method (BWM) implementation for multi-criteria decision making.
This module provides functionality to calculate criteria weights using the BWM approach
with linear programming optimization.
"""

import numpy as np
from scipy.optimize import linprog
from typing import Dict, List, Tuple, Optional
import json

class BestWorstMethod:
    """
    Best-Worst Method implementation for calculating criteria weights.
    
    The BWM reduces the number of comparisons needed compared to AHP while
    maintaining consistency. It only requires comparisons between:
    1. Best criterion vs all others
    2. All others vs worst criterion
    """
    
    def __init__(self):
        self.criteria = []
        self.best_criterion = None
        self.worst_criterion = None
        self.best_to_others = {}
        self.others_to_worst = {}
        self.weights = {}
        self.consistency_ratio = None
    
    def set_criteria(self, criteria: List[str]) -> None:
        """Set the list of criteria names."""
        self.criteria = criteria
        self.weights = {criterion: 0.0 for criterion in criteria}
    
    def set_best_worst(self, best: str, worst: str) -> None:
        """Set the best and worst criteria."""
        if best not in self.criteria or worst not in self.criteria:
            raise ValueError("Best and worst criteria must be in the criteria list")
        if best == worst:
            raise ValueError("Best and worst criteria must be different")
        
        self.best_criterion = best
        self.worst_criterion = worst
    
    def set_best_to_others(self, comparisons: Dict[str, float]) -> None:
        """
        Set the comparison values from best criterion to all others.
        
        Args:
            comparisons: Dictionary mapping criterion names to comparison values (1-9)
                        where 1 = equally important, 9 = best is extremely more important
        """
        for criterion, value in comparisons.items():
            if criterion not in self.criteria:
                raise ValueError(f"Criterion '{criterion}' not in criteria list")
            if not 1 <= value <= 9:
                raise ValueError(f"Comparison value must be between 1 and 9, got {value}")
        
        self.best_to_others = comparisons.copy()
        # Best criterion compared to itself is always 1
        self.best_to_others[self.best_criterion] = 1.0
    
    def set_others_to_worst(self, comparisons: Dict[str, float]) -> None:
        """
        Set the comparison values from all others to worst criterion.
        
        Args:
            comparisons: Dictionary mapping criterion names to comparison values (1-9)
                        where 1 = equally important, 9 = criterion is extremely more important than worst
        """
        for criterion, value in comparisons.items():
            if criterion not in self.criteria:
                raise ValueError(f"Criterion '{criterion}' not in criteria list")
            if not 1 <= value <= 9:
                raise ValueError(f"Comparison value must be between 1 and 9, got {value}")
        
        self.others_to_worst = comparisons.copy()
        # Worst criterion compared to itself is always 1
        self.others_to_worst[self.worst_criterion] = 1.0
    
    def calculate_weights(self) -> Tuple[Dict[str, float], float]:
        """
        Calculate the optimal weights using linear programming.
        
        Returns:
            Tuple of (weights_dict, consistency_ratio)
        """
        if not self.criteria or not self.best_criterion or not self.worst_criterion:
            raise ValueError("Must set criteria, best, and worst before calculating weights")
        
        if not self.best_to_others or not self.others_to_worst:
            raise ValueError("Must set comparison values before calculating weights")
        
        n = len(self.criteria)
        
        # Create variable mapping: w_1, w_2, ..., w_n, xi
        # Variables: [w_0, w_1, ..., w_{n-1}, xi]
        criterion_to_index = {criterion: i for i, criterion in enumerate(self.criteria)}
        best_idx = criterion_to_index[self.best_criterion]
        worst_idx = criterion_to_index[self.worst_criterion]
        
        # Objective: minimize xi (last variable)
        c = np.zeros(n + 1)
        c[-1] = 1.0  # Minimize xi
        
        # Constraints
        A_ub = []
        b_ub = []
        
        # Constraint 1: Best-to-Others comparisons
        # For each j != Best: w_Best - k_BO(j) * w_j <= xi
        # For each j != Best: k_BO(j) * w_j - w_Best <= xi
        for criterion in self.criteria:
            if criterion != self.best_criterion:
                j_idx = criterion_to_index[criterion]
                k_bo = self.best_to_others[criterion]
                
                # w_Best - k_BO(j) * w_j <= xi
                # Rearranged: w_Best - k_BO(j) * w_j - xi <= 0
                constraint1 = np.zeros(n + 1)
                constraint1[best_idx] = 1.0
                constraint1[j_idx] = -k_bo
                constraint1[-1] = -1.0
                A_ub.append(constraint1)
                b_ub.append(0.0)
                
                # k_BO(j) * w_j - w_Best <= xi
                # Rearranged: k_BO(j) * w_j - w_Best - xi <= 0
                constraint2 = np.zeros(n + 1)
                constraint2[j_idx] = k_bo
                constraint2[best_idx] = -1.0
                constraint2[-1] = -1.0
                A_ub.append(constraint2)
                b_ub.append(0.0)
        
        # Constraint 2: Others-to-Worst comparisons
        # For each i != Worst: w_i - k_OW(i) * w_Worst <= xi
        # For each i != Worst: k_OW(i) * w_Worst - w_i <= xi
        for criterion in self.criteria:
            if criterion != self.worst_criterion:
                i_idx = criterion_to_index[criterion]
                k_ow = self.others_to_worst[criterion]
                
                # w_i - k_OW(i) * w_Worst <= xi
                # Rearranged: w_i - k_OW(i) * w_Worst - xi <= 0
                constraint3 = np.zeros(n + 1)
                constraint3[i_idx] = 1.0
                constraint3[worst_idx] = -k_ow
                constraint3[-1] = -1.0
                A_ub.append(constraint3)
                b_ub.append(0.0)
                
                # k_OW(i) * w_Worst - w_i <= xi
                # Rearranged: k_OW(i) * w_Worst - w_i - xi <= 0
                constraint4 = np.zeros(n + 1)
                constraint4[worst_idx] = k_ow
                constraint4[i_idx] = -1.0
                constraint4[-1] = -1.0
                A_ub.append(constraint4)
                b_ub.append(0.0)
        
        # Equality constraint: sum of weights = 1
        A_eq = np.zeros(n + 1)
        A_eq[:n] = 1.0  # w_1 + w_2 + ... + w_n = 1
        A_eq = A_eq.reshape(1, -1)
        b_eq = np.array([1.0])
        
        # Bounds: weights >= 0, xi >= 0
        bounds = [(0, None) for _ in range(n + 1)]
        
        # Solve the linear program
        result = linprog(
            c=c,
            A_ub=np.array(A_ub) if A_ub else None,
            b_ub=np.array(b_ub) if b_ub else None,
            A_eq=A_eq,
            b_eq=b_eq,
            bounds=bounds,
            method='highs'
        )
        
        if not result.success:
            raise RuntimeError(f"Linear programming failed: {result.message}")
        
        # Extract results
        solution = result.x
        weights = solution[:n]
        consistency_ratio = solution[-1]
        
        # Update weights dictionary
        for i, criterion in enumerate(self.criteria):
            self.weights[criterion] = float(weights[i])
        
        self.consistency_ratio = float(consistency_ratio)
        
        return self.weights.copy(), self.consistency_ratio
    
    def get_consistency_interpretation(self) -> str:
        """
        Get a human-readable interpretation of the consistency ratio.
        
        Returns:
            String describing the consistency level
        """
        if self.consistency_ratio is None:
            return "No consistency ratio calculated"
        
        if self.consistency_ratio <= 0.1:
            return "Excellent consistency"
        elif self.consistency_ratio <= 0.2:
            return "Good consistency"
        elif self.consistency_ratio <= 0.3:
            return "Acceptable consistency"
        else:
            return "Poor consistency - consider revising comparisons"
    
    def to_dict(self) -> Dict:
        """Convert the BWM results to a dictionary for JSON serialization."""
        return {
            "criteria": self.criteria,
            "best_criterion": self.best_criterion,
            "worst_criterion": self.worst_criterion,
            "best_to_others": self.best_to_others,
            "others_to_worst": self.others_to_worst,
            "weights": self.weights,
            "consistency_ratio": self.consistency_ratio,
            "consistency_interpretation": self.get_consistency_interpretation()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BestWorstMethod':
        """Create a BWM instance from a dictionary."""
        bwm = cls()
        bwm.criteria = data.get("criteria", [])
        bwm.best_criterion = data.get("best_criterion")
        bwm.worst_criterion = data.get("worst_criterion")
        bwm.best_to_others = data.get("best_to_others", {})
        bwm.others_to_worst = data.get("others_to_worst", {})
        bwm.weights = data.get("weights", {})
        bwm.consistency_ratio = data.get("consistency_ratio")
        return bwm


def calculate_bwm_weights(criteria: List[str], best: str, worst: str, 
                         best_to_others: Dict[str, float], 
                         others_to_worst: Dict[str, float]) -> Dict:
    """
    Convenience function to calculate BWM weights.
    
    Args:
        criteria: List of criterion names
        best: Name of the best (most important) criterion
        worst: Name of the worst (least important) criterion
        best_to_others: Comparison values from best to all others (1-9 scale)
        others_to_worst: Comparison values from all others to worst (1-9 scale)
    
    Returns:
        Dictionary containing weights and consistency information
    """
    bwm = BestWorstMethod()
    bwm.set_criteria(criteria)
    bwm.set_best_worst(best, worst)
    bwm.set_best_to_others(best_to_others)
    bwm.set_others_to_worst(others_to_worst)
    
    weights, consistency_ratio = bwm.calculate_weights()
    
    return bwm.to_dict()


# Example usage and testing
if __name__ == "__main__":
    # Example: Price, Quality, Delivery, Sustainability
    criteria = ["Price", "Quality", "Delivery", "Sustainability"]
    best = "Price"  # Most important
    worst = "Sustainability"  # Least important
    
    # Best-to-Others: How much more important is Price compared to others?
    best_to_others = {
        "Price": 1,      # Price vs Price = 1 (equal)
        "Quality": 2,    # Price is moderately more important than Quality
        "Delivery": 4,   # Price is more important than Delivery
        "Sustainability": 8  # Price is much more important than Sustainability
    }
    
    # Others-to-Worst: How much more important is each criterion compared to Sustainability?
    others_to_worst = {
        "Price": 8,      # Price is much more important than Sustainability
        "Quality": 4,    # Quality is more important than Sustainability
        "Delivery": 2,   # Delivery is moderately more important than Sustainability
        "Sustainability": 1  # Sustainability vs Sustainability = 1 (equal)
    }
    
    try:
        result = calculate_bwm_weights(criteria, best, worst, best_to_others, others_to_worst)
        print("BWM Results:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")