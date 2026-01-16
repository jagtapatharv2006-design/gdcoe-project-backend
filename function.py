"""
High-Pay Potential Score (HPPS) Calculation System
Error-proof implementation with comprehensive fallbacks and validation.
"""

import math


def safe_float(value, default=None):
    """Safely convert value to float, handling None, strings, NaN, inf."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return default
        return float(value)
    if isinstance(value, str):
        try:
            converted = float(value)
            if math.isnan(converted) or math.isinf(converted):
                return default
            return converted
        except (ValueError, TypeError):
            return default
    return default


def safe_int(value, default=None):
    """Safely convert value to int."""
    float_val = safe_float(value, default)
    if float_val is None:
        return default
    try:
        return int(float_val)
    except (ValueError, TypeError):
        return default


def validate_ratio(value, name, warnings):
    """Validate and normalize ratio to [0, 1]. Returns 0.5 if invalid/missing."""
    num_val = safe_float(value)
    if num_val is None:
        warnings.append(f"{name} missing, using neutral fallback 0.5")
        return 0.5
    if num_val < 0:
        warnings.append(f"{name} negative ({value}), clamping to 0")
        return 0.0
    if num_val > 1.0:
        warnings.append(f"{name} > 1.0 ({value}), clamping to 1.0")
        return 1.0
    return float(num_val)


def validate_count(value, name, warnings):
    """Validate count. Returns 0 if invalid/missing."""
    num_val = safe_int(value)
    if num_val is None:
        warnings.append(f"{name} missing, using fallback 0")
        return 0
    if num_val < 0:
        warnings.append(f"{name} negative ({value}), clamping to 0")
        return 0
    return num_val


def validate_rating(value, name, warnings):
    """Validate rating. Returns None if invalid."""
    num_val = safe_float(value)
    if num_val is None:
        return None
    if num_val < 0:
        warnings.append(f"{name} negative ({value}), treating as missing")
        return None
    return num_val


def validate_ai_score(value, name, warnings):
    """Validate AI score (0-100 or 0-1 scale). Returns 50.0 if invalid/missing."""
    num_val = safe_float(value)
    if num_val is None:
        warnings.append(f"{name} missing, using neutral fallback 50.0")
        return 50.0
    if num_val < 0:
        warnings.append(f"{name} negative ({value}), clamping to 0")
        return 0.0
    return float(num_val)


def cf_percentile_safe(codeforces_rating):
    """Convert Codeforces rating to percentile (0-100 scale). Returns 50 if invalid."""
    try:
        if codeforces_rating is None:
            return 50.0
        rating = float(codeforces_rating)
        if rating >= 3000: return 99.93
        if rating >= 2400: return 99.2
        if rating >= 2100: return 97.0
        if rating >= 1900: return 94.0
        if rating >= 1600: return 85.0
        if rating >= 1400: return 73.0
        if rating >= 1200: return 55.0
        if rating >= 1000: return 33.0
        if rating >= 800: return 11.0
        return 5.0
    except (ValueError, TypeError, OverflowError):
        return 50.0


def lc_percentile_safe(leetcode_rating):
    """Convert LeetCode rating to percentile (0-100 scale). Returns 50 if invalid."""
    try:
        if leetcode_rating is None:
            return 50.0
        rating = float(leetcode_rating)
        if rating >= 2500: return 97.63
        if rating >= 2200: return 91.19
        if rating >= 2000: return 79.98
        if rating >= 1850: return 63.77
        if rating >= 1750: return 49.98
        if rating >= 1600: return 27.35
        if rating >= 1500: return 15.09
        if rating >= 1400: return 6.66
        if rating >= 1200: return 0.83
        if rating >= 1000: return 0.4
        return 0.1
    except (ValueError, TypeError, OverflowError):
        return 50.0


def get_best_rating_percentile(CF_rating, LC_rating, warnings):
    """Get best available rating percentile with fallback logic: CF → LC → 50."""
    cf_valid = validate_rating(CF_rating, "CF_rating", warnings)
    lc_valid = validate_rating(LC_rating, "LC_rating", warnings)
    
    if cf_valid is not None and lc_valid is not None:
        try:
            if cf_valid >= 0.75 * lc_valid:
                return cf_percentile_safe(cf_valid)
            else:
                return lc_percentile_safe(lc_valid)
        except (TypeError, ValueError, OverflowError):
            pass
    
    if cf_valid is not None:
        return cf_percentile_safe(cf_valid)
    
    if lc_valid is not None:
        return lc_percentile_safe(lc_valid)
    
    warnings.append("Both CF_rating and LC_rating missing, using neutral baseline 50 percentile")
    return 50.0


def norm(value, min_val=0, max_val=100):
    """Normalize value to 0-1 scale with safe bounds."""
    try:
        val = float(value)
        if max_val == min_val:
            return 0.0
        normalized = (val - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, normalized))
    except (ValueError, TypeError, ZeroDivisionError, OverflowError):
        return 0.0


def norm_percentile(percentile_value):
    """Normalize percentile (0-100 scale) to 0-1."""
    return norm(percentile_value, 0, 100)


def norm_ratio(ratio_value):
    """Normalize ratio (0-1 scale) - pass through with clamping."""
    try:
        val = float(ratio_value)
        return max(0.0, min(1.0, val))
    except (ValueError, TypeError):
        return 0.0


def norm_count(count_value, max_count=50):
    """Normalize count values."""
    return norm(count_value, 0, max_count)


def normalize_ai_score(value, threshold=10.0):
    """Normalize AI score: values > threshold treated as 0-100 scale, else 0-1."""
    try:
        val = float(value)
        if val > threshold:
            return norm_percentile(val)
        else:
            return norm_ratio(val)
    except (ValueError, TypeError):
        return 0.0


def calculate_AD(CF_rating, LC_rating, CF_hard_problem_ratio, LC_medium_hard_ratio, warnings):
    """Algorithmic Depth: AD = 0.6 * norm(rating) + 0.25 * norm(CF_hard) + 0.15 * norm(LC_medium_hard)"""
    try:
        best_percent = get_best_rating_percentile(CF_rating, LC_rating, warnings)
        norm_rating = norm_percentile(best_percent)
        
        norm_cf_hard = norm_ratio(validate_ratio(CF_hard_problem_ratio, "CF_hard_problem_ratio", warnings))
        norm_lc_medium_hard = norm_ratio(validate_ratio(LC_medium_hard_ratio, "LC_medium_hard_ratio", warnings))
        
        AD = 0.6 * norm_rating + 0.25 * norm_cf_hard + 0.15 * norm_lc_medium_hard
        return max(0.0, min(1.0, AD))
    except Exception as e:
        warnings.append(f"Error in calculate_AD: {str(e)}")
        return 0.5


def calculate_EAP(real_projects_count, project_complexity_score, stack_diversity, code_quality_indicators, warnings):
    """Execution & Application Power: EAP = 0.4 * norm(projects) + 0.25 * norm(complexity) + 0.2 * norm(stack) + 0.15 * norm(quality)"""
    try:
        projects = validate_count(real_projects_count, "real_projects_count", warnings)
        norm_projects = norm_count(projects, max_count=50)
        
        complexity = validate_ai_score(project_complexity_score, "project_complexity_score", warnings)
        stack = validate_ai_score(stack_diversity, "stack_diversity", warnings)
        quality = validate_ai_score(code_quality_indicators, "code_quality_indicators", warnings)
        
        norm_complexity = normalize_ai_score(complexity)
        norm_stack = normalize_ai_score(stack)
        norm_quality = normalize_ai_score(quality)
        
        EAP = 0.4 * norm_projects + 0.25 * norm_complexity + 0.2 * norm_stack + 0.15 * norm_quality
        return max(0.0, min(1.0, EAP))
    except Exception as e:
        warnings.append(f"Error in calculate_EAP: {str(e)}")
        return 0.5


def calculate_CCL(active_months, activity_frequency, rating_stability, longest_streak, warnings):
    """Consistency & Career Longevity: CCL = 0.4 * norm(months) + 0.25 * norm(frequency) + 0.2 * norm(stability) + 0.15 * norm(streak)"""
    try:
        months = validate_count(active_months, "active_months", warnings)
        norm_months = norm_count(months, max_count=60)
        
        freq = safe_float(activity_frequency)
        if freq is None:
            warnings.append("activity_frequency missing, using neutral fallback 0.5")
            norm_frequency = 0.5
        elif freq <= 1.0:
            norm_frequency = norm_ratio(freq)
        else:
            norm_frequency = norm_count(freq, max_count=30)
        
        stability = safe_float(rating_stability)
        if stability is None:
            warnings.append("rating_stability missing, using neutral fallback 0.5")
            norm_stability = 0.5
        elif stability <= 1.0:
            norm_stability = norm_ratio(stability)
        else:
            norm_stability = norm_percentile(stability)
        
        streak = validate_count(longest_streak, "longest_streak", warnings)
        norm_streak = norm_count(streak, max_count=365)
        
        CCL = 0.4 * norm_months + 0.25 * norm_frequency + 0.2 * norm_stability + 0.15 * norm_streak
        return max(0.0, min(1.0, CCL))
    except Exception as e:
        warnings.append(f"Error in calculate_CCL: {str(e)}")
        return 0.5


def calculate_LA(new_tech_usage, reusable_components, oss_engagement, cross_domain_work, warnings):
    """Leverage & Adaptability: LA = 0.35 * norm(new_tech) + 0.25 * norm(reusable) + 0.2 * norm(oss) + 0.2 * norm(cross)"""
    try:
        new_tech = validate_ai_score(new_tech_usage, "new_tech_usage", warnings)
        reusable = validate_ai_score(reusable_components, "reusable_components", warnings)
        oss = validate_ai_score(oss_engagement, "oss_engagement", warnings)
        cross = validate_ai_score(cross_domain_work, "cross_domain_work", warnings)
        
        norm_new_tech = normalize_ai_score(new_tech)
        norm_reusable = normalize_ai_score(reusable)
        norm_oss = normalize_ai_score(oss)
        norm_cross = normalize_ai_score(cross)
        
        LA = 0.35 * norm_new_tech + 0.25 * norm_reusable + 0.2 * norm_oss + 0.2 * norm_cross
        return max(0.0, min(1.0, LA))
    except Exception as e:
        warnings.append(f"Error in calculate_LA: {str(e)}")
        return 0.5


def apply_min_dominance_penalty(AD, EAP, CCL, penalty_min=0.3, penalty_max=0.5, warnings=None):
    """
    Apply non-linear minimum dominance penalty:
    If min(AD, EAP, CCL) < 0.4, reduce final HPPS by 30-50%.
    """
    try:
        min_score = min(AD, EAP, CCL)
        if min_score < 0.4:
            penalty = penalty_min + (penalty_max - penalty_min) * (0.4 - min_score) / 0.4
            if warnings is not None:
                warnings.append(f"Minimum dominance rule applied: penalty {penalty*100:.1f}%")
            return 1.0 - penalty
        return 1.0
    except Exception as e:
        if warnings is not None:
            warnings.append(f"Error in apply_min_dominance_penalty: {str(e)}")
        return 1.0


def apply_non_linear_penalty(AD, EAP, CCL, penalty_range=(0.3, 0.5)):
    """Apply 30-50% penalty if min(AD, EAP, CCL) < 0.4"""
    try:
        min_score = min(AD, EAP, CCL)
        if min_score >= 0.4:
            return 1.0
        
        min_penalty, max_penalty = penalty_range
        distance_below = 0.4 - min_score
        max_distance = 0.4
        
        penalty_factor = 1.0 - (min_penalty + (max_penalty - min_penalty) * (distance_below / max_distance))
        return max(penalty_range[0], min(1.0, penalty_factor))
    except Exception:
        return 1.0


def calculate_HPPS(
    CF_rating=None,
    LC_rating=None,
    CF_hard_problem_ratio=None,
    LC_medium_hard_ratio=None,
    real_projects_count=None,
    active_months=None,
    activity_frequency=None,
    rating_stability=None,
    longest_streak=None,
    project_complexity_score=50.0,
    code_quality_indicators=50.0,
    stack_diversity=50.0,
    reusable_components=50.0,
    cross_domain_work=50.0,
    oss_engagement=50.0,
    new_tech_usage=50.0
):
    """
    Calculate High-Pay Potential Score (HPPS) with full error handling.
    Returns HPPS, sub-scores, warnings, and errors.
    Never raises exceptions.
    """
    warnings = []
    errors = []
    
    try:
        AD = calculate_AD(CF_rating, LC_rating, CF_hard_problem_ratio, LC_medium_hard_ratio, warnings)
        EAP = calculate_EAP(real_projects_count, project_complexity_score, stack_diversity, code_quality_indicators, warnings)
        CCL = calculate_CCL(active_months, activity_frequency, rating_stability, longest_streak, warnings)
        LA = calculate_LA(new_tech_usage, reusable_components, oss_engagement, cross_domain_work, warnings)
        
        penalty_factor = apply_min_dominance_penalty(AD, EAP, CCL, warnings=warnings)
        base_HPPS = 0.30 * AD + 0.30 * EAP + 0.25 * CCL + 0.15 * LA
        final_HPPS = penalty_factor * base_HPPS
        
        return {
            'HPPS': max(0.0, min(1.0, final_HPPS)),
            'HPPS_percentage': max(0.0, min(100.0, final_HPPS * 100)),
            'AD': max(0.0, min(1.0, AD)),
            'EAP': max(0.0, min(1.0, EAP)),
            'CCL': max(0.0, min(1.0, CCL)),
            'LA': max(0.0, min(1.0, LA)),
            'penalty_applied': penalty_factor < 1.0,
            'penalty_multiplier': penalty_factor,
            'base_HPPS': max(0.0, min(1.0, base_HPPS)),
            'warnings': warnings,
            'errors': errors
        }
    except Exception as e:
        errors.append(f"Critical error in calculate_HPPS: {str(e)}")
        return {
            'HPPS': 0.0,
            'HPPS_percentage': 0.0,
            'AD': 0.0,
            'EAP': 0.0,
            'CCL': 0.0,
            'LA': 0.0,
            'penalty_applied': False,
            'penalty_multiplier': 1.0,
            'base_HPPS': 0.0,
            'warnings': warnings,
            'errors': errors
        }


if __name__ == "__main__":
    result = calculate_HPPS(
        CF_rating=2100,
        CF_hard_problem_ratio=0.15,
        LC_medium_hard_ratio=0.25,
        real_projects_count=10,
        active_months=24,
        activity_frequency=0.8,
        rating_stability=0.85,
        longest_streak=120,
        project_complexity_score=75.0,
        code_quality_indicators=80.0,
        stack_diversity=70.0,
        reusable_components=60.0,
        cross_domain_work=65.0,
        oss_engagement=50.0,
        new_tech_usage=70.0
    )
    
    print("HPPS Calculation Results:")
    print(f"Final HPPS: {result['HPPS']:.4f} ({result['HPPS_percentage']:.2f}%)")
    print(f"AD: {result['AD']:.4f}, EAP: {result['EAP']:.4f}, CCL: {result['CCL']:.4f}, LA: {result['LA']:.4f}")
    print(f"Penalty Applied: {result['penalty_applied']}, Multiplier: {result['penalty_multiplier']:.2f}")
    if result['warnings']:
        print(f"\nWarnings: {result['warnings']}")
    if result['errors']:
        print(f"\nErrors: {result['errors']}")
