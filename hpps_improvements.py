"""
HPPS System Improvements - Critical Fixes
Implements validation, improved normalization, and configuration management.
"""

from typing import Optional, Union, Tuple, Dict
from dataclasses import dataclass
import warnings


# ==================== CONFIGURATION ====================

@dataclass
class HPPSConfig:
    """Configuration for HPPS calculation system"""
    # Normalization bounds
    max_projects: int = 50
    max_active_months: int = 60
    max_streak_days: int = 365
    max_activity_frequency: int = 30
    
    # Default values for missing AI inputs
    default_ai_score: float = 50.0
    
    # Penalty configuration
    penalty_threshold: float = 0.4
    penalty_range: Tuple[float, float] = (0.3, 0.5)
    
    # Rating selection
    rating_selection_ratio: float = 0.75  # CF >= 0.75 * LC
    
    # Scale detection threshold (values > this are treated as 0-100 scale)
    ai_scale_threshold: float = 10.0


# ==================== VALIDATION ====================

class ValidationError(ValueError):
    """Raised when input validation fails"""
    pass


def validate_rating(rating: Optional[Union[int, float]], platform: str = "generic") -> Optional[Union[int, float]]:
    """Validate rating value"""
    if rating is None:
        return None
    if not isinstance(rating, (int, float)):
        raise ValidationError(f"{platform} rating must be numeric, got {type(rating).__name__}")
    if rating < 0:
        warnings.warn(f"{platform} rating is negative ({rating}), clamping to 0", UserWarning)
        return 0.0
    return float(rating)


def validate_ratio(ratio: Optional[float], name: str = "ratio") -> Optional[float]:
    """Validate ratio value in [0, 1]"""
    if ratio is None:
        return None
    if not isinstance(ratio, (int, float)):
        raise ValidationError(f"{name} must be numeric, got {type(ratio).__name__}")
    ratio = float(ratio)
    if ratio < 0:
        warnings.warn(f"{name} is negative ({ratio}), clamping to 0", UserWarning)
        return 0.0
    if ratio > 1.0:
        warnings.warn(f"{name} > 1.0 ({ratio}), clamping to 1.0", UserWarning)
        return 1.0
    return ratio


def validate_non_negative_count(count: Optional[Union[int, float]], name: str = "count") -> Optional[Union[int, float]]:
    """Validate non-negative count value"""
    if count is None:
        return None
    if not isinstance(count, (int, float)):
        raise ValidationError(f"{name} must be numeric, got {type(count).__name__}")
    if count < 0:
        warnings.warn(f"{name} is negative ({count}), clamping to 0", UserWarning)
        return 0
    return float(count) if isinstance(count, float) else int(count)


def validate_ai_score(score: Optional[float], name: str = "ai_score") -> Optional[float]:
    """Validate AI-driven score (0-100 or 0-1 scale)"""
    if score is None:
        return None
    if not isinstance(score, (int, float)):
        raise ValidationError(f"{name} must be numeric, got {type(score).__name__}")
    score = float(score)
    if score < 0:
        warnings.warn(f"{name} is negative ({score}), clamping to 0", UserWarning)
        return 0.0
    # Allow values up to 100 (will be normalized later)
    if score > 100:
        warnings.warn(f"{name} > 100 ({score}), assuming 0-100 scale", UserWarning)
    return score


# ==================== IMPROVED NORMALIZATION ====================

def norm(value: float, min_val: float = 0, max_val: float = 100) -> float:
    """
    Normalize a value to 0-1 scale with bounds checking.
    
    :param value: The value to normalize
    :param min_val: Minimum expected value (default: 0)
    :param max_val: Maximum expected value (default: 100)
    :return: Normalized value between 0 and 1
    :raises ValueError: If max_val == min_val
    """
    if max_val == min_val:
        raise ValueError(f"Cannot normalize when max_val ({max_val}) == min_val ({min_val})")
    normalized = (value - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, normalized))  # Clamp between 0 and 1


def norm_percentile(percentile_value: float) -> float:
    """Normalize percentile (0-100 scale) to 0-1"""
    return norm(percentile_value, 0, 100)


def norm_ratio(ratio_value: float) -> float:
    """Normalize ratio (0-1 scale) - pass through with clamping"""
    return max(0.0, min(1.0, float(ratio_value)))


def norm_count(count_value: float, max_count: int) -> float:
    """Normalize count values with configurable maximum"""
    return norm(float(count_value), 0, float(max_count))


def normalize_ai_score(value: float, config: HPPSConfig, explicit_scale: Optional[str] = None) -> float:
    """
    Normalize AI-driven score with explicit or auto-detected scale.
    
    Uses stricter heuristic: values > threshold are treated as 0-100 scale.
    This is more reliable than checking <= 1.0.
    
    :param value: Score value
    :param config: HPPS configuration
    :param explicit_scale: '0-1' or '0-100' or None for auto-detect
    :return: Normalized score (0-1)
    """
    if explicit_scale is None:
        # Auto-detect: values > threshold assumed to be 0-100 scale
        explicit_scale = '0-100' if value > config.ai_scale_threshold else '0-1'
    
    if explicit_scale == '0-1':
        return norm_ratio(value)
    else:  # '0-100'
        return norm_percentile(value)


# ==================== IMPROVED RATING FUNCTIONS ====================

def cf_percentile_improved(codeforces_rating: Union[int, float]) -> float:
    """Convert Codeforces rating to percentile (0-100 scale) with validation"""
    if not isinstance(codeforces_rating, (int, float)) or codeforces_rating < 0:
        raise ValidationError(f"Invalid CF rating: {codeforces_rating}")
    
    if codeforces_rating >= 3000: return 99.93
    if codeforces_rating >= 2400: return 99.2
    if codeforces_rating >= 2100: return 97
    if codeforces_rating >= 1900: return 94
    if codeforces_rating >= 1600: return 85
    if codeforces_rating >= 1400: return 73
    if codeforces_rating >= 1200: return 55
    if codeforces_rating >= 1000: return 33
    if codeforces_rating >= 800: return 11
    return 5


def lc_percentile_improved(leetcode_rating: Union[int, float]) -> float:
    """Convert LeetCode rating to percentile (0-100 scale) with validation"""
    if not isinstance(leetcode_rating, (int, float)) or leetcode_rating < 0:
        raise ValidationError(f"Invalid LC rating: {leetcode_rating}")
    
    if leetcode_rating >= 2500: return 97.63
    if leetcode_rating >= 2200: return 91.19
    if leetcode_rating >= 2000: return 79.98
    if leetcode_rating >= 1850: return 63.77
    if leetcode_rating >= 1750: return 49.98
    if leetcode_rating >= 1600: return 27.35
    if leetcode_rating >= 1500: return 15.09
    if leetcode_rating >= 1400: return 6.66
    if leetcode_rating >= 1200: return 0.83
    if leetcode_rating >= 1000: return 0.4
    return 0.1


# ==================== IMPROVED CALCULATION FUNCTIONS ====================

def calculate_AD_improved(
    CF_rating: Optional[Union[int, float]] = None,
    LC_rating: Optional[Union[int, float]] = None,
    CF_hard_problem_ratio: Optional[float] = None,
    LC_medium_hard_ratio: Optional[float] = None,
    config: Optional[HPPSConfig] = None
) -> float:
    """
    Algorithmic Depth (AD) with improved validation and None handling.
    
    AD = 0.6 * norm(best_rating) + 0.25 * norm(CF_hard_problem_ratio) + 0.15 * norm(LC_medium_hard_ratio)
    """
    if config is None:
        config = HPPSConfig()
    
    # Validate inputs
    CF_rating = validate_rating(CF_rating, "codeforces")
    LC_rating = validate_rating(LC_rating, "leetcode")
    CF_hard_problem_ratio = validate_ratio(CF_hard_problem_ratio, "CF_hard_problem_ratio")
    LC_medium_hard_ratio = validate_ratio(LC_medium_hard_ratio, "LC_medium_hard_ratio")
    
    # Select best rating
    best_rating = None
    best_percent = 0.0
    
    if CF_rating is not None and LC_rating is not None:
        if CF_rating >= config.rating_selection_ratio * LC_rating:
            best_rating = CF_rating
            best_percent = cf_percentile_improved(CF_rating)
        else:
            best_rating = LC_rating
            best_percent = lc_percentile_improved(LC_rating)
    elif CF_rating is not None:
        best_percent = cf_percentile_improved(CF_rating)
    elif LC_rating is not None:
        best_percent = lc_percentile_improved(LC_rating)
    # else: best_percent remains 0.0
    
    norm_best_rating = norm_percentile(best_percent)
    norm_cf_hard = norm_ratio(CF_hard_problem_ratio) if CF_hard_problem_ratio is not None else 0.0
    norm_lc_medium_hard = norm_ratio(LC_medium_hard_ratio) if LC_medium_hard_ratio is not None else 0.0
    
    AD = 0.6 * norm_best_rating + 0.25 * norm_cf_hard + 0.15 * norm_lc_medium_hard
    return max(0.0, min(1.0, AD))


def calculate_EAP_improved(
    real_projects_count: Optional[Union[int, float]] = None,
    project_complexity_score: Optional[float] = None,
    stack_diversity: Optional[float] = None,
    code_quality_indicators: Optional[float] = None,
    config: Optional[HPPSConfig] = None
) -> float:
    """
    Execution & Application Power (EAP) with improved validation.
    
    EAP = 0.4 * norm(real_projects_count) + 0.25 * norm(project_complexity_score)
        + 0.2 * norm(stack_diversity) + 0.15 * norm(code_quality_indicators)
    """
    if config is None:
        config = HPPSConfig()
    
    # Validate and handle None
    real_projects_count = validate_non_negative_count(real_projects_count, "real_projects_count") or 0
    project_complexity_score = validate_ai_score(project_complexity_score, "project_complexity_score") or config.default_ai_score
    stack_diversity = validate_ai_score(stack_diversity, "stack_diversity") or config.default_ai_score
    code_quality_indicators = validate_ai_score(code_quality_indicators, "code_quality_indicators") or config.default_ai_score
    
    norm_projects = norm_count(real_projects_count, config.max_projects)
    norm_complexity = normalize_ai_score(project_complexity_score, config)
    norm_stack = normalize_ai_score(stack_diversity, config)
    norm_quality = normalize_ai_score(code_quality_indicators, config)
    
    EAP = 0.4 * norm_projects + 0.25 * norm_complexity + 0.2 * norm_stack + 0.15 * norm_quality
    return max(0.0, min(1.0, EAP))


# ==================== SANITY CHECKS ====================

def sanity_check_result(result: Dict) -> bool:
    """Verify HPPS result is within expected bounds"""
    assert 0 <= result['HPPS'] <= 1, f"HPPS out of bounds: {result['HPPS']}"
    assert all(0 <= result[k] <= 1 for k in ['AD', 'EAP', 'CCL', 'LA']), "Sub-scores out of bounds"
    assert 0 < result['penalty_multiplier'] <= 1, f"Invalid penalty multiplier: {result['penalty_multiplier']}"
    assert 0 <= result['base_HPPS'] <= 1, f"Base HPPS out of bounds: {result['base_HPPS']}"
    return True


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    config = HPPSConfig()
    
    # Test improved functions
    print("Testing improved AD calculation:")
    ad_score = calculate_AD_improved(
        CF_rating=2100,
        LC_rating=None,
        CF_hard_problem_ratio=0.15,
        LC_medium_hard_ratio=0.25,
        config=config
    )
    print(f"AD Score: {ad_score:.4f}")
    
    print("\nTesting improved EAP calculation:")
    eap_score = calculate_EAP_improved(
        real_projects_count=10,
        project_complexity_score=75.0,
        stack_diversity=70.0,
        code_quality_indicators=80.0,
        config=config
    )
    print(f"EAP Score: {eap_score:.4f}")
    
    print("\nTesting edge cases:")
    # Test with missing inputs
    ad_minimal = calculate_AD_improved(CF_rating=1600, config=config)
    print(f"AD with minimal inputs: {ad_minimal:.4f}")
    
    # Test with None (should use defaults)
    eap_defaults = calculate_EAP_improved(real_projects_count=5, config=config)
    print(f"EAP with AI defaults: {eap_defaults:.4f}")
