"""
Layer-0 Code Analyzer for HPPS
Analyzes local Git repositories to extract code-analysis-based metrics.
Error-proof implementation with comprehensive fallbacks.
"""

import os
import subprocess
import json
import re
import math
from pathlib import Path
from collections import defaultdict, Counter


# ============================================================================
# Utility Functions
# ============================================================================

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


def run_command(cmd, cwd=None, timeout=30):
    """Run shell command safely and return stdout, stderr, return_code."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timeout", -1
    except Exception as e:
        return "", str(e), -1


def find_python_files(repo_path):
    """Find all Python files in the repository."""
    try:
        python_files = []
        for root, dirs, files in os.walk(repo_path):
            # Skip common directories
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', '.env'}]
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        return python_files
    except Exception:
        return []


def get_file_lines(file_path):
    """Count lines in a file, handling errors."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return len(f.readlines())
    except Exception:
        return 0


# ============================================================================
# Complexity Analysis Functions
# ============================================================================

def analyze_complexity_radon(repo_path, warnings):
    """Analyze cyclomatic complexity using radon."""
    try:
        stdout, stderr, returncode = run_command(
            f"radon cc --min B --json .",
            cwd=repo_path,
            timeout=60
        )
        if returncode != 0:
            warnings.append("radon not available, using fallback complexity analysis")
            return None
        
        try:
            data = json.loads(stdout)
            return data
        except json.JSONDecodeError:
            return None
    except Exception as e:
        warnings.append(f"radon analysis failed: {str(e)}")
        return None


def get_complexity_fallback(python_files):
    """Fallback complexity estimation based on file size and structure."""
    try:
        total_complexity = 0
        function_count = 0
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # Count functions and classes (rough estimate)
                functions = len(re.findall(r'^\s*def\s+\w+', content, re.MULTILINE))
                classes = len(re.findall(r'^\s*class\s+\w+', content, re.MULTILINE))
                
                # Estimate complexity: functions * 2 + classes * 3
                file_complexity = functions * 2 + classes * 3
                total_complexity += file_complexity
                function_count += functions
            except Exception:
                continue
        
        return {
            'total_complexity': total_complexity,
            'function_count': function_count,
            'avg_complexity': total_complexity / max(function_count, 1)
        }
    except Exception:
        return {'total_complexity': 0, 'function_count': 0, 'avg_complexity': 0}


def calculate_CF_hard_problem_ratio(repo_path, warnings):
    """Calculate ratio of high-complexity functions (complexity >= 10)."""
    try:
        python_files = find_python_files(repo_path)
        if not python_files:
            warnings.append("No Python files found, using default CF_hard_problem_ratio")
            return 0.0
        
        radon_data = analyze_complexity_radon(repo_path, warnings)
        
        high_complexity_count = 0
        total_functions = 0
        
        if radon_data:
            # Parse radon JSON output
            for file_path, file_data in radon_data.items():
                if isinstance(file_data, list):
                    for item in file_data:
                        if 'complexity' in item:
                            total_functions += 1
                            if item['complexity'] >= 10:
                                high_complexity_count += 1
        else:
            # Fallback: estimate from file analysis
            fallback_data = get_complexity_fallback(python_files)
            total_functions = fallback_data['function_count']
            # Estimate: functions with high avg complexity
            if fallback_data['avg_complexity'] >= 5:
                high_complexity_count = int(total_functions * 0.2)
            else:
                high_complexity_count = int(total_functions * 0.05)
        
        if total_functions == 0:
            return 0.0
        
        ratio = high_complexity_count / total_functions
        return max(0.0, min(1.0, ratio))
    except Exception as e:
        warnings.append(f"Error calculating CF_hard_problem_ratio: {str(e)}")
        return 0.0


def calculate_LC_medium_hard_ratio(repo_path, warnings):
    """Calculate ratio of medium/high complexity functions (complexity >= 6)."""
    try:
        python_files = find_python_files(repo_path)
        if not python_files:
            warnings.append("No Python files found, using default LC_medium_hard_ratio")
            return 0.0
        
        radon_data = analyze_complexity_radon(repo_path, warnings)
        
        medium_high_count = 0
        total_functions = 0
        
        if radon_data:
            for file_path, file_data in radon_data.items():
                if isinstance(file_data, list):
                    for item in file_data:
                        if 'complexity' in item:
                            total_functions += 1
                            if item['complexity'] >= 6:
                                medium_high_count += 1
        else:
            fallback_data = get_complexity_fallback(python_files)
            total_functions = fallback_data['function_count']
            if fallback_data['avg_complexity'] >= 4:
                medium_high_count = int(total_functions * 0.4)
            else:
                medium_high_count = int(total_functions * 0.15)
        
        if total_functions == 0:
            return 0.0
        
        ratio = medium_high_count / total_functions
        return max(0.0, min(1.0, ratio))
    except Exception as e:
        warnings.append(f"Error calculating LC_medium_hard_ratio: {str(e)}")
        return 0.0


# ============================================================================
# Project Count Analysis
# ============================================================================

def calculate_real_projects_count(repo_path, warnings):
    """Count distinct projects in the repository based on setup.py, requirements.txt, package.json, etc."""
    try:
        projects = set()
        
        # Look for project indicators
        for root, dirs, files in os.walk(repo_path):
            # Skip .git and common build directories
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', '.env', 'build', 'dist'}]
            
            # Check for Python projects
            if 'setup.py' in files or 'pyproject.toml' in files or 'requirements.txt' in files:
                projects.add(root)
            
            # Check for Node.js projects
            if 'package.json' in files:
                projects.add(root)
            
            # Check for other project files
            if 'pom.xml' in files or 'build.gradle' in files:  # Java
                projects.add(root)
            if 'Cargo.toml' in files:  # Rust
                projects.add(root)
            if 'go.mod' in files:  # Go
                projects.add(root)
            if 'composer.json' in files:  # PHP
                projects.add(root)
        
        count = len(projects)
        if count == 0:
            # Fallback: count top-level directories with significant content
            try:
                top_level_dirs = [d for d in os.listdir(repo_path) 
                                if os.path.isdir(os.path.join(repo_path, d)) 
                                and not d.startswith('.')]
                # Filter by having multiple files (likely a project)
                count = sum(1 for d in top_level_dirs 
                          if len(os.listdir(os.path.join(repo_path, d))) > 3)
                if count == 0:
                    count = 1  # At least one project (the repo itself)
            except Exception:
                count = 1
        
        return max(1, count)
    except Exception as e:
        warnings.append(f"Error calculating real_projects_count: {str(e)}")
        return 1


# ============================================================================
# Project Complexity Score
# ============================================================================

def calculate_project_complexity_score(repo_path, warnings):
    """Calculate normalized complexity score based on LOC and cyclomatic complexity."""
    try:
        python_files = find_python_files(repo_path)
        total_loc = 0
        
        for file_path in python_files:
            total_loc += get_file_lines(file_path)
        
        # Get cyclomatic complexity
        radon_data = analyze_complexity_radon(repo_path, warnings)
        total_complexity = 0
        
        if radon_data:
            for file_path, file_data in radon_data.items():
                if isinstance(file_data, list):
                    for item in file_data:
                        if 'complexity' in item:
                            total_complexity += item['complexity']
        else:
            fallback_data = get_complexity_fallback(python_files)
            total_complexity = fallback_data['total_complexity']
        
        # Normalize: LOC component (0-50) + Complexity component (0-50)
        # Target: 10000 LOC = 50, 500 complexity = 50
        loc_score = min(50.0, (total_loc / 10000.0) * 50.0)
        complexity_score = min(50.0, (total_complexity / 500.0) * 50.0)
        
        combined_score = loc_score + complexity_score
        return max(0.0, min(100.0, combined_score))
    except Exception as e:
        warnings.append(f"Error calculating project_complexity_score: {str(e)}")
        return 50.0


# ============================================================================
# Code Quality Indicators
# ============================================================================

def analyze_with_pylint(repo_path, warnings):
    """Run pylint and extract score."""
    try:
        python_files = find_python_files(repo_path)
        if not python_files:
            return None
        
        # Try with one representative file
        test_file = python_files[0]
        stdout, stderr, returncode = run_command(
            f"pylint --score=yes {test_file}",
            cwd=repo_path,
            timeout=30
        )
        
        # Extract score from output (format: "Your code has been rated at X.XX/10")
        match = re.search(r'rated at\s+([\d.]+)/10', stdout)
        if match:
            return float(match.group(1)) * 10.0  # Convert to 0-100 scale
        return None
    except Exception:
        return None


def analyze_with_ruff(repo_path, warnings):
    """Run ruff and estimate quality score."""
    try:
        stdout, stderr, returncode = run_command(
            "ruff check . --output-format=json",
            cwd=repo_path,
            timeout=60
        )
        
        if returncode == 0 and not stdout.strip():
            # No issues found
            return 100.0
        
        try:
            issues = json.loads(stdout)
            issue_count = len(issues) if isinstance(issues, list) else 0
            
            # Estimate score: fewer issues = higher score
            # Normalize: 0 issues = 100, 100+ issues = 50
            if issue_count == 0:
                return 100.0
            score = max(50.0, 100.0 - (issue_count / 2.0))
            return score
        except (json.JSONDecodeError, TypeError):
            return None
    except Exception:
        return None


def calculate_code_quality_indicators(repo_path, warnings):
    """Calculate combined code quality score from linting tools."""
    try:
        scores = []
        
        # Try pylint
        pylint_score = analyze_with_pylint(repo_path, warnings)
        if pylint_score is not None:
            scores.append(pylint_score)
        
        # Try ruff
        ruff_score = analyze_with_ruff(repo_path, warnings)
        if ruff_score is not None:
            scores.append(ruff_score)
        
        if not scores:
            warnings.append("No linting tools available, using default code_quality_indicators")
            return 50.0
        
        # Average available scores
        avg_score = sum(scores) / len(scores)
        return max(0.0, min(100.0, avg_score))
    except Exception as e:
        warnings.append(f"Error calculating code_quality_indicators: {str(e)}")
        return 50.0


# ============================================================================
# Stack Diversity
# ============================================================================

def detect_languages(repo_path):
    """Detect programming languages used in the repository."""
    try:
        languages = set()
        extensions_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.go': 'Go',
            '.rs': 'Rust',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.scala': 'Scala',
            '.r': 'R',
            '.sql': 'SQL',
            '.html': 'HTML',
            '.css': 'CSS',
            '.sh': 'Shell',
            '.yml': 'YAML',
            '.yaml': 'YAML',
            '.json': 'JSON',
        }
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', '.env', 'build', 'dist'}]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in extensions_map:
                    languages.add(extensions_map[ext])
        
        return languages
    except Exception:
        return set()


def calculate_stack_diversity(repo_path, warnings):
    """Calculate stack diversity score based on detected languages."""
    try:
        languages = detect_languages(repo_path)
        
        # Score: more languages = higher diversity
        # 1 language = 20, 2-3 = 40, 4-5 = 60, 6-8 = 80, 9+ = 100
        lang_count = len(languages)
        
        if lang_count == 0:
            return 20.0
        elif lang_count == 1:
            return 20.0
        elif lang_count <= 3:
            return 20.0 + (lang_count - 1) * 10.0
        elif lang_count <= 5:
            return 40.0 + (lang_count - 3) * 10.0
        elif lang_count <= 8:
            return 60.0 + (lang_count - 5) * 6.67
        else:
            return min(100.0, 80.0 + (lang_count - 8) * 2.5)
    except Exception as e:
        warnings.append(f"Error calculating stack_diversity: {str(e)}")
        return 50.0


# ============================================================================
# Reusable Components
# ============================================================================

def calculate_reusable_components(repo_path, warnings):
    """Calculate ratio of modular/reusable code components."""
    try:
        python_files = find_python_files(repo_path)
        if not python_files:
            warnings.append("No Python files found, using default reusable_components")
            return 50.0
        
        reusable_count = 0
        total_modules = 0
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Check for modular patterns
                has_classes = bool(re.search(r'^\s*class\s+\w+', content, re.MULTILINE))
                has_functions = bool(re.search(r'^\s*def\s+\w+', content, re.MULTILINE))
                has_docstrings = '"""' in content or "'''" in content
                has_type_hints = ':' in content and '->' in content  # Basic type hint detection
                is_main = '__main__' in content  # Less reusable if it's a main script
                
                total_modules += 1
                
                # Score modularity: classes + functions + docs + type hints - main scripts
                modularity_score = 0
                if has_classes:
                    modularity_score += 1
                if has_functions:
                    modularity_score += 1
                if has_docstrings:
                    modularity_score += 1
                if has_type_hints:
                    modularity_score += 1
                if is_main:
                    modularity_score -= 1
                
                if modularity_score >= 2:
                    reusable_count += 1
            except Exception:
                continue
        
        if total_modules == 0:
            return 50.0
        
        ratio = reusable_count / total_modules
        # Convert ratio to 0-100 scale
        score = ratio * 100.0
        return max(0.0, min(100.0, score))
    except Exception as e:
        warnings.append(f"Error calculating reusable_components: {str(e)}")
        return 50.0


# ============================================================================
# Cross-Domain Work
# ============================================================================

def calculate_cross_domain_work(repo_path, warnings):
    """Calculate ratio of files touching multiple modules or directories."""
    try:
        python_files = find_python_files(repo_path)
        if len(python_files) < 2:
            return 50.0
        
        cross_domain_count = 0
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Count imports from different paths
                imports = re.findall(r'^from\s+([\w.]+)\s+import|^import\s+([\w.]+)', content, re.MULTILINE)
                import_paths = set()
                
                for match in imports:
                    path = match[0] or match[1]
                    # Extract top-level module
                    top_level = path.split('.')[0]
                    import_paths.add(top_level)
                
                # File is cross-domain if it imports from 3+ different top-level modules
                if len(import_paths) >= 3:
                    cross_domain_count += 1
            except Exception:
                continue
        
        ratio = cross_domain_count / len(python_files)
        score = ratio * 100.0
        return max(0.0, min(100.0, score))
    except Exception as e:
        warnings.append(f"Error calculating cross_domain_work: {str(e)}")
        return 50.0


# ============================================================================
# OSS Engagement
# ============================================================================

def calculate_oss_engagement(repo_path, warnings):
    """Calculate number of external dependencies/packages used."""
    try:
        dependency_count = 0
        
        # Check requirements.txt
        req_file = os.path.join(repo_path, 'requirements.txt')
        if os.path.exists(req_file):
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    dependency_count += len(deps)
            except Exception:
                pass
        
        # Check pyproject.toml
        pyproject_file = os.path.join(repo_path, 'pyproject.toml')
        if os.path.exists(pyproject_file):
            try:
                with open(pyproject_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Simple regex match for dependencies
                    deps = re.findall(r'^\s*[\w-]+[\w]*\s*=.*', content, re.MULTILINE)
                    dependency_count += len(deps) // 2  # Rough estimate
            except Exception:
                pass
        
        # Check package.json
        package_file = os.path.join(repo_path, 'package.json')
        if os.path.exists(package_file):
            try:
                with open(package_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    deps = data.get('dependencies', {})
                    dev_deps = data.get('devDependencies', {})
                    dependency_count += len(deps) + len(dev_deps)
            except Exception:
                pass
        
        # Normalize: 0 deps = 20, 10 deps = 50, 30 deps = 80, 50+ deps = 100
        if dependency_count == 0:
            return 20.0
        elif dependency_count <= 10:
            return 20.0 + (dependency_count / 10.0) * 30.0
        elif dependency_count <= 30:
            return 50.0 + ((dependency_count - 10) / 20.0) * 30.0
        else:
            return min(100.0, 80.0 + ((dependency_count - 30) / 20.0) * 20.0)
    except Exception as e:
        warnings.append(f"Error calculating oss_engagement: {str(e)}")
        return 50.0


# ============================================================================
# New Tech Usage
# ============================================================================

def detect_new_tech(repo_path):
    """Detect new or unusual languages/frameworks."""
    try:
        tech_signals = set()
        
        # Modern Python frameworks
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules'}]
            
            if 'FastAPI' in str(files) or 'fastapi' in str(root):
                tech_signals.add('FastAPI')
            if 'flask' in str(files).lower():
                tech_signals.add('Flask')
            if 'django' in str(files).lower():
                tech_signals.add('Django')
            if 'pytest' in str(files).lower() or 'pytest.ini' in files:
                tech_signals.add('pytest')
            
            # Modern JS frameworks
            if 'package.json' in files:
                try:
                    with open(os.path.join(root, 'package.json'), 'r') as f:
                        data = json.load(f)
                        deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                        if 'react' in str(deps).lower():
                            tech_signals.add('React')
                        if 'vue' in str(deps).lower():
                            tech_signals.add('Vue')
                        if 'angular' in str(deps).lower():
                            tech_signals.add('Angular')
                        if 'typescript' in str(deps).lower():
                            tech_signals.add('TypeScript')
                        if 'next' in str(deps).lower():
                            tech_signals.add('Next.js')
                except Exception:
                    pass
        
        # Check for Rust, Go, modern languages
        languages = detect_languages(repo_path)
        if 'Rust' in languages:
            tech_signals.add('Rust')
        if 'Go' in languages:
            tech_signals.add('Go')
        if 'TypeScript' in languages:
            tech_signals.add('TypeScript')
        
        return tech_signals
    except Exception:
        return set()


def calculate_new_tech_usage(repo_path, warnings):
    """Calculate score based on detection of new/unusual technologies."""
    try:
        new_tech = detect_new_tech(repo_path)
        
        # Score: more modern tech = higher score
        # 0 tech = 30, 1-2 = 50, 3-4 = 70, 5-6 = 85, 7+ = 100
        tech_count = len(new_tech)
        
        if tech_count == 0:
            return 30.0
        elif tech_count <= 2:
            return 30.0 + (tech_count / 2.0) * 20.0
        elif tech_count <= 4:
            return 50.0 + ((tech_count - 2) / 2.0) * 20.0
        elif tech_count <= 6:
            return 70.0 + ((tech_count - 4) / 2.0) * 15.0
        else:
            return min(100.0, 85.0 + (tech_count - 6) * 3.0)
    except Exception as e:
        warnings.append(f"Error calculating new_tech_usage: {str(e)}")
        return 50.0


# ============================================================================
# Main Analysis Function
# ============================================================================

def analyze_repo(repo_path):
    """
    Analyze a Git repository and return code-analysis-based HPPS metrics.
    
    Args:
        repo_path: Path to the Git repository
        
    Returns:
        dict with HPPS metrics, warnings, and errors
    """
    warnings = []
    errors = []
    
    # Validate repo_path
    if not repo_path or not os.path.exists(repo_path):
        errors.append(f"Repository path does not exist: {repo_path}")
        return _get_default_output(warnings, errors)
    
    if not os.path.isdir(repo_path):
        errors.append(f"Repository path is not a directory: {repo_path}")
        return _get_default_output(warnings, errors)
    
    try:
        # Calculate all metrics
        CF_hard_problem_ratio = calculate_CF_hard_problem_ratio(repo_path, warnings)
        LC_medium_hard_ratio = calculate_LC_medium_hard_ratio(repo_path, warnings)
        real_projects_count = calculate_real_projects_count(repo_path, warnings)
        project_complexity_score = calculate_project_complexity_score(repo_path, warnings)
        code_quality_indicators = calculate_code_quality_indicators(repo_path, warnings)
        stack_diversity = calculate_stack_diversity(repo_path, warnings)
        reusable_components = calculate_reusable_components(repo_path, warnings)
        cross_domain_work = calculate_cross_domain_work(repo_path, warnings)
        oss_engagement = calculate_oss_engagement(repo_path, warnings)
        new_tech_usage = calculate_new_tech_usage(repo_path, warnings)
        
        return {
            'CF_hard_problem_ratio': CF_hard_problem_ratio,
            'LC_medium_hard_ratio': LC_medium_hard_ratio,
            'real_projects_count': real_projects_count,
            'project_complexity_score': project_complexity_score,
            'code_quality_indicators': code_quality_indicators,
            'stack_diversity': stack_diversity,
            'reusable_components': reusable_components,
            'cross_domain_work': cross_domain_work,
            'oss_engagement': oss_engagement,
            'new_tech_usage': new_tech_usage,
            'warnings': warnings,
            'errors': errors
        }
    except Exception as e:
        errors.append(f"Critical error in analyze_repo: {str(e)}")
        return _get_default_output(warnings, errors)


def _get_default_output(warnings, errors):
    """Return default output dictionary with safe fallback values."""
    return {
        'CF_hard_problem_ratio': 0.0,
        'LC_medium_hard_ratio': 0.0,
        'real_projects_count': 1,
        'project_complexity_score': 50.0,
        'code_quality_indicators': 50.0,
        'stack_diversity': 50.0,
        'reusable_components': 50.0,
        'cross_domain_work': 50.0,
        'oss_engagement': 50.0,
        'new_tech_usage': 50.0,
        'warnings': warnings,
        'errors': errors
    }


# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python layer0_code_analyzer.py <repo_path>")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    result = analyze_repo(repo_path)
    
    # Print JSON output
    print(json.dumps(result, indent=2))
    
    # Print summary
    print("\n=== Analysis Summary ===")
    print(f"CF_hard_problem_ratio: {result['CF_hard_problem_ratio']:.4f}")
    print(f"LC_medium_hard_ratio: {result['LC_medium_hard_ratio']:.4f}")
    print(f"real_projects_count: {result['real_projects_count']}")
    print(f"project_complexity_score: {result['project_complexity_score']:.2f}")
    print(f"code_quality_indicators: {result['code_quality_indicators']:.2f}")
    print(f"stack_diversity: {result['stack_diversity']:.2f}")
    print(f"reusable_components: {result['reusable_components']:.2f}")
    print(f"cross_domain_work: {result['cross_domain_work']:.2f}")
    print(f"oss_engagement: {result['oss_engagement']:.2f}")
    print(f"new_tech_usage: {result['new_tech_usage']:.2f}")
    
    if result['warnings']:
        print(f"\nWarnings ({len(result['warnings'])}):")
        for w in result['warnings']:
            print(f"  - {w}")
    
    if result['errors']:
        print(f"\nErrors ({len(result['errors'])}):")
        for e in result['errors']:
            print(f"  - {e}")
