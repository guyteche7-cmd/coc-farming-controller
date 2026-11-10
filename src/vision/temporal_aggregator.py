import time
import logging
from typing import Callable, List, Optional, Tuple, Any
import numpy as np

logger = logging.getLogger(__name__)

class TemporalAggregator:
    @staticmethod
    def aggregate(
        fetch_callback: Callable[[], Tuple[Any, float]],
        num_samples: int = 5,
        delay_between_samples: float = 0.05,
        min_confidence: float = 0.4
    ) -> Tuple[Any, float]:
        """
        Calls `fetch_callback` multiple times.
        Expected return of fetch_callback: (value, confidence).
        Filters out None/invalid values and low confidence.
        Removes statistical outliers and clusters nearby values.
        Returns the consensus value and average confidence of the consensus cluster.
        """
        observations = []
        for _ in range(num_samples):
            val, conf = fetch_callback()
            if val is not None and conf >= min_confidence:
                # Basic type checking to ensure it's a number for stats
                if isinstance(val, (int, float)):
                    observations.append((val, conf))
                elif isinstance(val, str) and val.strip():
                    observations.append((val, conf))
            time.sleep(delay_between_samples)

        if not observations:
            return None, 0.0
            
        # Separate numbers and strings
        if isinstance(observations[0][0], (int, float)):
            return TemporalAggregator._aggregate_numbers(observations)
        else:
            return TemporalAggregator._aggregate_strings(observations)
            
    @staticmethod
    def _aggregate_numbers(observations: List[Tuple[float, float]]) -> Tuple[float, float]:
        values = np.array([o[0] for o in observations])
        confs = np.array([o[1] for o in observations])
        
        # 1. Remove statistical outliers using IQR
        if len(values) >= 4:
            q1, q3 = np.percentile(values, [25, 75])
            iqr = q3 - q1
            # Using 1.0 IQR for tighter clustering given OCR errors
            lower_bound = q1 - (1.0 * iqr)
            upper_bound = q3 + (1.0 * iqr)
            
            mask = (values >= lower_bound) & (values <= upper_bound)
            values = values[mask]
            confs = confs[mask]
            
        if len(values) == 0:
            return None, 0.0
            
        # 2. Cluster nearby values (Tolerance based clustering)
        sorted_indices = np.argsort(values)
        values = values[sorted_indices]
        confs = confs[sorted_indices]
        
        clusters = []
        current_cluster = [0]
        
        for i in range(1, len(values)):
            # If within 5% or exactly equal, consider it the same cluster
            if abs(values[i] - values[i-1]) <= max(1, 0.05 * values[i-1]):
                current_cluster.append(i)
            else:
                clusters.append(current_cluster)
                current_cluster = [i]
        clusters.append(current_cluster)
        
        # 3. Find the best cluster (most elements, then highest sum of confidence)
        best_cluster = max(clusters, key=lambda c: (len(c), np.sum(confs[c])))
        
        # 4. Use median or weighted consensus
        cluster_values = values[best_cluster]
        cluster_confs = confs[best_cluster]
        
        weight_sum = np.sum(cluster_confs)
        if weight_sum > 0:
            consensus = np.sum(cluster_values * cluster_confs) / weight_sum
        else:
            consensus = np.median(cluster_values)
            
        if all(isinstance(v, int) or v.is_integer() for v in cluster_values):
            consensus = int(round(consensus))
            
        avg_conf = np.mean(cluster_confs)
        return consensus, avg_conf

    @staticmethod
    def _aggregate_strings(observations: List[Tuple[str, float]]) -> Tuple[str, float]:
        freq = {}
        for val, conf in observations:
            if val not in freq:
                freq[val] = {'count': 0, 'conf_sum': 0.0}
            freq[val]['count'] += 1
            freq[val]['conf_sum'] += conf
            
        best_val = max(freq.keys(), key=lambda k: (freq[k]['count'], freq[k]['conf_sum']))
        avg_conf = freq[best_val]['conf_sum'] / freq[best_val]['count']
        return best_val, avg_conf
