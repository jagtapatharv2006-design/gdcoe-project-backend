"""
Job Matching Layer for HPPS
Handles job description processing, keyword extraction, and student matching.
Error-proof implementation with comprehensive fallbacks.
"""

import os
import json
import re
import math
import uuid
from typing import Dict, List, Optional, Any


KEYWORD_MAP = {
    "rest_api": ["backend"],
    "api": ["backend"],
    "flask": ["backend", "python"],
    "django": ["backend", "python"],
    "fastapi": ["backend", "python"],
    "express": ["backend", "javascript"],
    "node": ["backend", "javascript"],
    "spring": ["backend", "java"],
    "rails": ["backend", "ruby"],
    "laravel": ["backend", "php"],
    "sql": ["database"],
    "mysql": ["database"],
    "postgresql": ["database"],
    "postgres": ["database"],
    "mongodb": ["database"],
    "redis": ["database"],
    "react": ["frontend", "javascript"],
    "vue": ["frontend", "javascript"],
    "angular": ["frontend", "javascript"],
    "typescript": ["javascript"],
    "javascript": ["javascript"],
    "python": ["python"],
    "java": ["java"],
    "cpp": ["c++"],
    "c++": ["c++"],
    "c": ["c"],
    "go": ["go"],
    "rust": ["rust"],
    "html": ["frontend"],
    "css": ["frontend"],
    "docker": ["devops"],
    "kubernetes": ["devops"],
    "k8s": ["devops"],
    "aws": ["cloud"],
    "azure": ["cloud"],
    "gcp": ["cloud"],
    "tensorflow": ["machine_learning"],
    "pytorch": ["machine_learning"],
    "sklearn": ["machine_learning"],
    "pandas": ["data_engineering"],
    "spark": ["data_engineering"],
    "etl": ["data_engineering"],
}


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


class GeminiProvider:
    """Provider abstraction for Gemini API calls."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Gemini API key. If None, attempts to read from GEMINI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._client = None
        self._initialized = False
    
    def _initialize_client(self):
        """Lazy initialization of Gemini client."""
        if self._initialized:
            return self._initialized
        
        if not self.api_key:
            return False
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel('gemini-pro')
            self._initialized = True
            return True
        except ImportError:
            return False
        except Exception:
            return False
    
    def extract_keywords(self, job_description: str, retry_count: int = 0) -> Dict[str, Any]:
        """
        Extract keywords from job description using Gemini.
        
        Args:
            job_description: Free text job description
            retry_count: Current retry attempt (0-2)
            
        Returns:
            Dict with job_role, keywords, mandatory_keywords, or empty dict on error
        """
        if not self.api_key:
            return {}
        
        if not self._initialize_client():
            return {}
        
        if not job_description or not isinstance(job_description, str):
            return {}
        
        try:
            if retry_count == 0:
                prompt = f"""Extract job role and keywords from this job description. Return ONLY valid JSON in this exact format:

{{
  "job_role": "<job role name>",
  "keywords": ["keyword1", "keyword2", ...],
  "mandatory_keywords": ["mandatory1", ...]
}}

Job description:
{job_description}

Return ONLY valid JSON. No explanation."""
            else:
                prompt = f"""Return ONLY valid JSON in the required schema. No explanation.

{{
  "job_role": "<job role name>",
  "keywords": ["keyword1", "keyword2", ...],
  "mandatory_keywords": ["mandatory1", ...]
}}

Job description:
{job_description}"""
            
            response = self._client.generate_content(prompt)
            text = response.text.strip()
            
            json_text = self._extract_json(text)
            if not json_text:
                if retry_count < 2:
                    return self.extract_keywords(job_description, retry_count + 1)
                return {}
            
            parsed = json.loads(json_text)
            validated = self._validate_keyword_response(parsed)
            
            if not validated and retry_count < 2:
                return self.extract_keywords(job_description, retry_count + 1)
            
            return validated if validated else {}
            
        except Exception:
            if retry_count < 2:
                return self.extract_keywords(job_description, retry_count + 1)
            return {}
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from text that may contain markdown or extra text."""
        if not text:
            return None
        
        text = text.strip()
        
        if text.startswith('```'):
            lines = text.split('\n')
            start_idx = -1
            end_idx = len(lines)
            
            for i, line in enumerate(lines):
                if line.strip().startswith('```'):
                    if start_idx == -1:
                        start_idx = i + 1
                    else:
                        end_idx = i
                        break
            
            if start_idx >= 0:
                text = '\n'.join(lines[start_idx:end_idx]).strip()
        
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx >= 0 and end_idx > start_idx:
            return text[start_idx:end_idx + 1]
        
        return text if text.startswith('{') else None
    
    def _validate_keyword_response(self, data: Any) -> Optional[Dict[str, Any]]:
        """Validate Gemini response structure."""
        if not isinstance(data, dict):
            return None
        
        job_role = data.get("job_role")
        keywords = data.get("keywords")
        mandatory_keywords = data.get("mandatory_keywords")
        
        if not isinstance(job_role, str):
            return None
        
        if not isinstance(keywords, list):
            return None
        
        if not isinstance(mandatory_keywords, list):
            return None
        
        if not all(isinstance(kw, str) for kw in keywords):
            return None
        
        if not all(isinstance(kw, str) for kw in mandatory_keywords):
            return None
        
        return {
            "job_role": job_role,
            "keywords": keywords,
            "mandatory_keywords": mandatory_keywords
        }


def normalize_keyword(keyword: str) -> Optional[str]:
    """Normalize a single keyword to snake_case lowercase."""
    if not keyword or not isinstance(keyword, str):
        return None
    
    keyword = keyword.strip().lower()
    if not keyword:
        return None
    
    keyword = re.sub(r'[^\w\s-]', '', keyword)
    keyword = re.sub(r'[\s-]+', '_', keyword)
    keyword = keyword.strip('_')
    
    return keyword if keyword else None


def normalize_keywords(keywords: List[str], max_count: int = 25) -> List[str]:
    """Normalize and deduplicate keywords."""
    if not keywords or not isinstance(keywords, list):
        return []
    
    normalized = []
    seen = set()
    
    for kw in keywords:
        normalized_kw = normalize_keyword(kw)
        if normalized_kw and normalized_kw not in seen:
            normalized.append(normalized_kw)
            seen.add(normalized_kw)
            
            if len(normalized) >= max_count:
                break
    
    return normalized


def normalize_student_field(field: Any) -> List[str]:
    """Normalize student field (skills, tags, languages) to list of normalized strings."""
    if not field:
        return []
    
    if isinstance(field, str):
        return [normalize_keyword(field)] if normalize_keyword(field) else []
    
    if isinstance(field, list):
        result = []
        for item in field:
            normalized = normalize_keyword(str(item)) if item else None
            if normalized:
                result.append(normalized)
        return result
    
    return []


def _check_keyword_match(keyword: str, all_student_keywords: set) -> bool:
    """Check if keyword matches using mapping layer or direct match."""
    if keyword in all_student_keywords:
        return True
    
    if keyword in KEYWORD_MAP:
        mapped_fields = KEYWORD_MAP[keyword]
        for field in mapped_fields:
            if field in all_student_keywords:
                return True
    
    return False


def calculate_keyword_match(student: Dict[str, Any], keywords: List[str], mandatory_keywords: List[str]) -> Optional[Dict[str, Any]]:
    """
    Calculate keyword match percentage for a student.
    
    Returns:
        Dict with matched_keywords, unmatched_keywords, total_keywords, match_pct, mandatory_matched, or None if invalid
    """
    if not student or not isinstance(student, dict):
        return None
    
    if not keywords or not isinstance(keywords, list):
        return None
    
    if not mandatory_keywords or not isinstance(mandatory_keywords, list):
        mandatory_keywords = []
    
    skills = normalize_student_field(student.get("skills", []))
    tags = normalize_student_field(student.get("tags", []))
    languages = normalize_student_field(student.get("languages", []))
    
    all_student_keywords = set(skills + tags + languages)
    
    matched = []
    unmatched = []
    for kw in keywords:
        if _check_keyword_match(kw, all_student_keywords):
            matched.append(kw)
        else:
            unmatched.append(kw)
    
    mandatory_matched = []
    mandatory_unmatched = []
    for mkw in mandatory_keywords:
        normalized_mkw = normalize_keyword(mkw)
        if normalized_mkw and _check_keyword_match(normalized_mkw, all_student_keywords):
            mandatory_matched.append(normalized_mkw)
        else:
            if normalized_mkw:
                mandatory_unmatched.append(normalized_mkw)
    
    total_keywords = len(keywords)
    matched_count = len(matched)
    
    if total_keywords == 0:
        match_pct = 0.0
    else:
        match_pct = matched_count / total_keywords
    
    mandatory_met = len(mandatory_matched) == len(mandatory_keywords) if mandatory_keywords else True
    
    return {
        "matched_keywords": matched,
        "unmatched_keywords": unmatched,
        "total_keywords": total_keywords,
        "match_pct": max(0.0, min(1.0, match_pct)),
        "mandatory_matched": mandatory_met,
        "mandatory_matched_keywords": mandatory_matched,
        "mandatory_unmatched_keywords": mandatory_unmatched,
        "mandatory_count": len(mandatory_keywords),
        "mandatory_matched_count": len(mandatory_matched)
    }


def generate_job_requests(qualified_students: List[Dict[str, Any]], job_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Generate job request objects for qualified students."""
    if not qualified_students:
        return []
    
    if not job_id:
        job_id = str(uuid.uuid4())
    
    requests = []
    for student in qualified_students:
        student_id = safe_int(student.get("student_id"))
        if student_id is None:
            continue
        
        keyword_match_pct = safe_float(student.get("keyword_match_pct"), 0.0)
        
        requests.append({
            "student_id": student_id,
            "job_id": job_id,
            "status": "PENDING",
            "keyword_match_pct": keyword_match_pct
        })
    
    return requests


def is_qualified(student_match: Dict[str, Any], min_match_threshold: float = 0.75) -> bool:
    """Check if student meets qualification criteria."""
    if not student_match:
        return False
    
    match_pct = safe_float(student_match.get("match_pct"), 0.0)
    mandatory_met = student_match.get("mandatory_matched", False)
    
    return match_pct >= min_match_threshold and mandatory_met


def rank_students(qualified_students: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Rank students by general_score and keyword_match_pct. Returns separate rankings."""
    if not qualified_students:
        return {"general_ranking": [], "job_specific_ranking": []}
    
    for idx, student in enumerate(qualified_students):
        general_score = safe_float(student.get("general_score"), 0.0)
        keyword_match_pct = safe_float(student.get("keyword_match_pct"), 0.0)
        
        student["general_score"] = general_score
        student["keyword_match_pct"] = keyword_match_pct
    
    general_ranked = sorted(qualified_students, key=lambda x: safe_float(x.get("general_score"), 0.0), reverse=True)
    job_ranked = sorted(qualified_students, key=lambda x: safe_float(x.get("keyword_match_pct"), 0.0), reverse=True)
    
    general_ranking = []
    for rank, student in enumerate(general_ranked, 1):
        student_id = safe_int(student.get("student_id"))
        if student_id is None:
            continue
        
        general_ranking.append({
            "student_id": student_id,
            "keyword_match_pct": safe_float(student.get("keyword_match_pct"), 0.0),
            "general_score": safe_float(student.get("general_score"), 0.0),
            "general_rank": rank,
            "matched_keywords": student.get("matched_keywords", []),
            "unmatched_keywords": student.get("unmatched_keywords", [])
        })
    
    job_specific_ranking = []
    for rank, student in enumerate(job_ranked, 1):
        student_id = safe_int(student.get("student_id"))
        if student_id is None:
            continue
        
        job_specific_ranking.append({
            "student_id": student_id,
            "keyword_match_pct": safe_float(student.get("keyword_match_pct"), 0.0),
            "general_score": safe_float(student.get("general_score"), 0.0),
            "job_rank": rank,
            "matched_keywords": student.get("matched_keywords", []),
            "unmatched_keywords": student.get("unmatched_keywords", [])
        })
    
    return {
        "general_ranking": general_ranking,
        "job_specific_ranking": job_specific_ranking
    }


def process_job_profile(job_description: str, students: List[Dict[str, Any]], gemini_api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Process job description, extract keywords, match students, and return rankings.
    
    Args:
        job_description: Free text job description
        students: List of student profile dictionaries
        gemini_api_key: Optional Gemini API key (uses env var if not provided)
        
    Returns:
        Dict with job_role, keywords, general_ranking, job_specific_ranking, job_requests, warnings, errors
    """
    warnings = []
    errors = []
    
    if not job_description or not isinstance(job_description, str):
        errors.append("job_description must be a non-empty string")
        return _get_default_output(warnings, errors)
    
    if not students or not isinstance(students, list):
        warnings.append("students list is empty or invalid")
        return _get_default_output(warnings, errors)
    
    try:
        provider = GeminiProvider(api_key=gemini_api_key)
        
        if not provider.api_key:
            errors.append("Job keyword extraction failed. Manual keywords required.")
            return _get_default_output(warnings, errors)
        
        keyword_data = provider.extract_keywords(job_description)
        
        if not keyword_data:
            errors.append("Job keyword extraction failed. Manual keywords required.")
            return _get_default_output(warnings, errors)
        
        job_role = keyword_data.get("job_role", "Unknown")
        raw_keywords = keyword_data.get("keywords", [])
        raw_mandatory = keyword_data.get("mandatory_keywords", [])
        
        keywords = normalize_keywords(raw_keywords, max_count=25)
        mandatory_keywords = normalize_keywords(raw_mandatory, max_count=10)
        
        if not keywords:
            errors.append("Job keyword extraction failed. Manual keywords required.")
            return _get_default_output(warnings, errors)
        
        qualified_students_raw = []
        
        for student in students:
            if not student or not isinstance(student, dict):
                continue
            
            student_id = safe_int(student.get("student_id"))
            if student_id is None:
                continue
            
            match_result = calculate_keyword_match(student, keywords, mandatory_keywords)
            if not match_result:
                continue
            
            if is_qualified(match_result, min_match_threshold=0.75):
                general_score = safe_float(student.get("general_score"), 0.0)
                
                qualified_students_raw.append({
                    "student_id": student_id,
                    "keyword_match_pct": match_result["match_pct"],
                    "general_score": general_score,
                    "matched_keywords": match_result.get("matched_keywords", []),
                    "unmatched_keywords": match_result.get("unmatched_keywords", [])
                })
        
        ranked_data = rank_students(qualified_students_raw)
        
        job_id = str(uuid.uuid4())
        job_requests = generate_job_requests(qualified_students_raw, job_id=job_id)
        
        return {
            "job_role": job_role,
            "keywords": keywords,
            "general_ranking": ranked_data.get("general_ranking", []),
            "job_specific_ranking": ranked_data.get("job_specific_ranking", []),
            "job_requests": job_requests,
            "warnings": warnings,
            "errors": errors
        }
        
    except Exception as e:
        errors.append(f"Critical error in process_job_profile: {str(e)}")
        return _get_default_output(warnings, errors)


def _get_default_output(warnings: List[str], errors: List[str]) -> Dict[str, Any]:
    """Return default output dictionary with safe fallback values."""
    return {
        "job_role": "Unknown",
        "keywords": [],
        "general_ranking": [],
        "job_specific_ranking": [],
        "job_requests": [],
        "warnings": warnings,
        "errors": errors
    }
