from typing import Dict, List, Optional, Tuple
import pandas as pd
import logging

from src.med_llm_evaluation.data_handler import DataHandler
from src.med_llm_evaluation.llm_evaluator import LLMEvaluator
from src.med_llm_evaluation.statistical_analyzer import StatisticalAnalyzer

logger = logging.getLogger(__name__)

class MedicalLLMEvaluator:
    """Main interface for evaluating LLM performance on medical questions."""

    def __init__(self, client, variant, cache_dir: str = ".cache/med_eval"):
        """
        Initialize the medical LLM evaluator.
        
        Args:
            client: The API client instance
            variant: The model variant to use
            cache_dir (str): Directory for caching downloaded data
        """
        self.data_handler = DataHandler(cache_dir)
        self.evaluator = LLMEvaluator(client, variant)
        self.analyzer = StatisticalAnalyzer()
    
    def run_evaluation(self,
                      k: int,
                      subject_name: Optional[str] = None,
                      random_seed: Optional[int] = None,
                      max_workers: int = 10,
                      alpha: float = 0.05) -> Tuple[float, float, pd.DataFrame, Dict]:
        """
        Run complete evaluation including statistical analysis.
        
        Args:
            k (int): Number of samples to evaluate
            subject_name (Optional[str]): Filter by subject name
            random_seed (Optional[int]): Random seed for reproducibility
            max_workers (int): Maximum number of concurrent API calls
            alpha (float): Significance level for statistical tests
            
        Returns:
            Tuple[float, float, pd.DataFrame, Dict]: 
                - Accuracy
                - Kappa score
                - Results DataFrame
                - Statistical analysis results
        """
        # Load data
        prompts, labels, subject_names = self.data_handler.load_data()
        
        # Filter by subject_name if provided
        X, y = self.data_handler.filter_by_subject(prompts, labels, subject_names, subject_name)
        
        if not X:  # Check if we have any data after filtering
            raise ValueError(f"No data found for subject: {subject_name}")

        if len(X) < k:
            raise ValueError(f"Not enough data for subject: {subject_name} (need {k}, have {len(X)})")

        # Run evaluation
        accuracy, kappa, results_df = self.evaluator.evaluate(
            X, y, k, random_seed, max_workers
        )
        
        # Perform statistical analysis on valid predictions
        valid_mask = results_df['predicted_answer'] != -1
        y_true_valid = results_df.loc[valid_mask, 'true_answer'].tolist()
        y_pred_valid = results_df.loc[valid_mask, 'predicted_answer'].tolist()
        
        stats_results = self.analyzer.analyze(y_true_valid, y_pred_valid, alpha)
        
        logger.info(stats_results['summary'])
        
        return accuracy, kappa, results_df, stats_results