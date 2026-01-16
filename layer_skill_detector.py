"""
Skill Tag Detection Layer for HPPS
Detects presence of high-level skills as boolean tags in Git repositories.
Error-proof implementation with comprehensive fallbacks.
"""

import os
import re
import json
from pathlib import Path


def safe_read_file(file_path):
    """Safely read file content, returning empty string on error."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        return ""


def find_files_by_pattern(repo_path, patterns, check_content=False):
    """Find files matching patterns in repository."""
    matches = []
    try:
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', '.env', 'build', 'dist'}]
            for file in files:
                for pattern in patterns:
                    if pattern in file.lower() or pattern in file:
                        file_path = os.path.join(root, file)
                        if check_content:
                            content = safe_read_file(file_path)
                            if content:
                                matches.append((file_path, content))
                        else:
                            matches.append(file_path)
        return matches
    except Exception:
        return []


def find_files_by_extension(repo_path, extensions):
    """Find all files with given extensions."""
    files = []
    try:
        for root, dirs, file_list in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', '.env'}]
            for file in file_list:
                ext = os.path.splitext(file)[1].lower()
                if ext in extensions:
                    files.append(os.path.join(root, file))
        return files
    except Exception:
        return []


def check_file_content_contains(file_path, keywords):
    """Check if file content contains any of the keywords."""
    try:
        content = safe_read_file(file_path).lower()
        for keyword in keywords:
            if keyword.lower() in content:
                return True
        return False
    except Exception:
        return False


def check_dependencies_file(file_path, keywords):
    """Check dependency files (requirements.txt, package.json, etc.) for keywords."""
    try:
        content = safe_read_file(file_path)
        if not content:
            return False
        content_lower = content.lower()
        for keyword in keywords:
            if keyword.lower() in content_lower:
                return True
        return False
    except Exception:
        return False


def detect_backend(repo_path, warnings):
    """Detect backend development skills."""
    try:
        signals = []
        
        backend_frameworks = ['flask', 'django', 'fastapi', 'express', 'spring', 'rails', 'laravel', 'gin', 'echo', 'nest']
        backend_files = ['app.py', 'main.py', 'server.py', 'app.js', 'server.js', 'index.js']
        backend_folders = ['api', 'routes', 'controllers', 'middleware', 'services', 'backend']
        
        config_files = ['requirements.txt', 'package.json', 'pom.xml', 'build.gradle', 'go.mod', 'composer.json', 'pyproject.toml']
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', '.env'}]
            
            for file in files:
                file_lower = file.lower()
                if any(fw in file_lower for fw in backend_frameworks):
                    signals.append(f"framework file: {file}")
                if file in backend_files:
                    signals.append(f"backend file: {file}")
                
                if file in config_files:
                    file_path = os.path.join(root, file)
                    if check_dependencies_file(file_path, backend_frameworks):
                        signals.append(f"framework in {file}")
            
            for dir_name in dirs:
                if dir_name.lower() in backend_folders:
                    signals.append(f"backend folder: {dir_name}")
        
        if len(signals) >= 2:
            return True
        
        python_files = find_files_by_extension(repo_path, ['.py'])
        for py_file in python_files[:10]:
            content = safe_read_file(py_file).lower()
            backend_imports = ['from flask', 'from django', 'from fastapi', 'import flask', 'import django', 'import fastapi', '@app.route', '@router.', 'from werkzeug', 'from aiohttp']
            if any(imp in content for imp in backend_imports):
                return True
        
        js_files = find_files_by_extension(repo_path, ['.js', '.ts'])
        for js_file in js_files[:10]:
            content = safe_read_file(js_file).lower()
            backend_imports = ['require(\'express\')', 'require("express")', 'from express', 'app.get', 'app.post', 'router.', '@nestjs', 'from koa']
            if any(imp in content for imp in backend_imports):
                return True
        
        return len(signals) >= 1
    except Exception as e:
        warnings.append(f"Error detecting backend: {str(e)}")
        return False


def detect_frontend(repo_path, warnings):
    """Detect frontend development skills."""
    try:
        signals = []
        
        frontend_frameworks = ['react', 'vue', 'angular', 'svelte', 'next.js', 'nuxt', 'gatsby']
        frontend_files = ['package.json', 'package-lock.json', 'yarn.lock', 'vite.config', 'webpack.config', 'rollup.config', 'tailwind.config']
        frontend_folders = ['src', 'public', 'components', 'pages', 'views', 'frontend', 'client', 'ui']
        frontend_extensions = ['.html', '.css', '.scss', '.sass', '.less', '.jsx', '.tsx']
        
        html_files = find_files_by_extension(repo_path, ['.html'])
        if html_files:
            signals.append("HTML files found")
        
        css_files = find_files_by_extension(repo_path, ['.css', '.scss', '.sass', '.less'])
        if css_files:
            signals.append("CSS files found")
        
        jsx_files = find_files_by_extension(repo_path, ['.jsx', '.tsx'])
        if jsx_files:
            signals.append("JSX/TSX files found")
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', '.env'}]
            
            for file in files:
                file_lower = file.lower()
                if any(fw in file_lower for fw in frontend_frameworks):
                    signals.append(f"frontend framework: {file}")
                
                if file in frontend_files:
                    file_path = os.path.join(root, file)
                    if file == 'package.json':
                        try:
                            content = safe_read_file(file_path)
                            data = json.loads(content)
                            deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                            deps_str = json.dumps(deps).lower()
                            if any(fw in deps_str for fw in frontend_frameworks):
                                signals.append("frontend framework in package.json")
                        except Exception:
                            pass
                    else:
                        signals.append(f"frontend config: {file}")
            
            for dir_name in dirs:
                if dir_name.lower() in frontend_folders:
                    signals.append(f"frontend folder: {dir_name}")
        
        if len(signals) >= 2:
            return True
        
        js_files = find_files_by_extension(repo_path, ['.js', '.jsx', '.ts', '.tsx'])
        for js_file in js_files[:10]:
            content = safe_read_file(js_file).lower()
            frontend_imports = ['react', 'vue', 'angular/core', 'from react', 'from vue', 'import react', 'document.', 'window.', 'localstorage']
            if any(imp in content for imp in frontend_imports):
                return True
        
        return len(signals) >= 1
    except Exception as e:
        warnings.append(f"Error detecting frontend: {str(e)}")
        return False


def detect_machine_learning(repo_path, warnings):
    """Detect machine learning skills."""
    try:
        signals = []
        
        ml_libraries = ['tensorflow', 'pytorch', 'torch', 'sklearn', 'scikit-learn', 'keras', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'xgboost', 'lightgbm', 'catboost']
        ml_files = ['train.py', 'model.py', 'train.ipynb', 'model.ipynb', 'notebook.ipynb', '.ipynb']
        ml_folders = ['models', 'notebooks', 'data', 'datasets', 'training', 'ml']
        
        notebook_files = find_files_by_extension(repo_path, ['.ipynb'])
        if notebook_files:
            signals.append("Jupyter notebooks found")
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', '.env'}]
            
            for file in files:
                file_lower = file.lower()
                if any(ml in file_lower for ml in ml_files):
                    signals.append(f"ML file: {file}")
            
            for dir_name in dirs:
                if dir_name.lower() in ml_folders:
                    signals.append(f"ML folder: {dir_name}")
        
        if len(signals) >= 1:
            return True
        
        python_files = find_files_by_extension(repo_path, ['.py'])
        for py_file in python_files[:20]:
            content = safe_read_file(py_file).lower()
            ml_imports = ['import tensorflow', 'import torch', 'import sklearn', 'from sklearn', 'import keras', 'from keras', 'import pandas', 'from pandas', 'import numpy', 'from numpy', 'import xgboost', 'from xgboost']
            ml_keywords = ['model.fit', 'model.predict', 'train_test_split', 'cross_val_score', 'neural_network', 'deep learning', 'gradient descent', '.fit(', '.predict(']
            if any(imp in content for imp in ml_imports) or any(kw in content for kw in ml_keywords):
                return True
        
        req_file = os.path.join(repo_path, 'requirements.txt')
        if os.path.exists(req_file):
            if check_dependencies_file(req_file, ml_libraries):
                return True
        
        pyproject_file = os.path.join(repo_path, 'pyproject.toml')
        if os.path.exists(pyproject_file):
            if check_dependencies_file(pyproject_file, ml_libraries):
                return True
        
        return False
    except Exception as e:
        warnings.append(f"Error detecting machine_learning: {str(e)}")
        return False


def detect_competitive_programming(repo_path, warnings):
    """Detect competitive programming skills."""
    try:
        signals = []
        
        cp_patterns = ['solution', 'solve', 'problem', 'codeforces', 'leetcode', 'atcoder', 'hackerrank', 'contest']
        cp_files_patterns = ['.cpp', '.c', '.java', '.py']
        
        all_files = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', '.env'}]
            all_files.extend([os.path.join(root, f) for f in files])
        
        file_count = len(all_files)
        if file_count > 50:
            signals.append(f"many files: {file_count}")
        
        small_files_count = 0
        short_files_count = 0
        
        for file_path in all_files[:100]:
            try:
                ext = os.path.splitext(file_path)[1].lower()
                if ext in cp_files_patterns:
                    file_name = os.path.basename(file_path).lower()
                    if any(pattern in file_name for pattern in cp_patterns):
                        signals.append(f"CP pattern in filename: {file_name}")
                    
                    content = safe_read_file(file_path)
                    lines = len(content.split('\n'))
                    if lines < 300:
                        small_files_count += 1
                    if lines < 100:
                        short_files_count += 1
            except Exception:
                continue
        
        if file_count > 30 and small_files_count > file_count * 0.7:
            signals.append("many small files pattern")
        
        if file_count > 30 and short_files_count > file_count * 0.4:
            signals.append("many very short files")
        
        framework_files = ['package.json', 'requirements.txt', 'setup.py', 'pom.xml', 'build.gradle', 'Cargo.toml']
        framework_count = sum(1 for f in all_files if os.path.basename(f) in framework_files)
        
        if file_count > 30 and framework_count == 0:
            signals.append("no framework files")
        
        python_files = find_files_by_extension(repo_path, ['.py'])
        fast_io_count = 0
        for py_file in python_files[:50]:
            content = safe_read_file(py_file).lower()
            if 'sys.stdin' in content or 'input()' in content or 'sys.stdout' in content or 'print(' in content:
                if 'flask' not in content and 'django' not in content and 'fastapi' not in content:
                    fast_io_count += 1
        
        if fast_io_count >= 5:
            signals.append("fast IO patterns")
        
        if len(signals) >= 3:
            return True
        
        if len(signals) >= 2 and file_count > 30:
            return True
        
        return False
    except Exception as e:
        warnings.append(f"Error detecting competitive_programming: {str(e)}")
        return False


def detect_devops(repo_path, warnings):
    """Detect DevOps skills."""
    try:
        signals = []
        
        devops_files = ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml', '.dockerignore', 'Jenkinsfile', 'dockerfile']
        ci_files = ['.github/workflows', '.gitlab-ci.yml', '.travis.yml', 'circleci', 'azure-pipelines.yml', '.github']
        k8s_files = ['kubernetes', 'k8s', 'deployment.yaml', 'service.yaml', 'configmap.yaml']
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules'}]
            
            for file in files:
                file_lower = file.lower()
                if file in devops_files or file_lower in devops_files:
                    signals.append(f"DevOps file: {file}")
                if file in ci_files or file_lower in ci_files:
                    signals.append(f"CI file: {file}")
                if any(k8s in file_lower for k8s in k8s_files):
                    signals.append(f"K8s file: {file}")
            
            for dir_name in dirs:
                dir_lower = dir_name.lower()
                if '.github' in dir_lower or 'ci' in dir_lower or 'cd' in dir_lower or 'deploy' in dir_lower:
                    signals.append(f"CI/CD folder: {dir_name}")
        
        yml_files = find_files_by_extension(repo_path, ['.yml', '.yaml'])
        for yml_file in yml_files:
            file_name = os.path.basename(yml_file).lower()
            if 'docker' in file_name or 'compose' in file_name or 'ci' in file_name or 'workflow' in file_name:
                signals.append(f"DevOps YAML: {file_name}")
        
        if len(signals) >= 1:
            return True
        
        return False
    except Exception as e:
        warnings.append(f"Error detecting devops: {str(e)}")
        return False


def detect_data_engineering(repo_path, warnings):
    """Detect data engineering skills."""
    try:
        signals = []
        
        sql_files = find_files_by_extension(repo_path, ['.sql'])
        if sql_files:
            signals.append(f"SQL files: {len(sql_files)}")
        
        etl_keywords = ['etl', 'extract', 'transform', 'load', 'pipeline', 'data pipeline', 'datawarehouse', 'data warehouse', 'datalake', 'data lake']
        de_folders = ['etl', 'pipelines', 'data_pipeline', 'data-pipeline', 'warehouse', 'transform', 'ingestion']
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env', '.env'}]
            
            for file in files:
                file_lower = file.lower()
                if any(keyword in file_lower for keyword in etl_keywords):
                    signals.append(f"ETL file: {file}")
            
            for dir_name in dirs:
                if dir_name.lower() in de_folders:
                    signals.append(f"DE folder: {dir_name}")
        
        if len(signals) >= 1:
            return True
        
        python_files = find_files_by_extension(repo_path, ['.py'])
        pandas_count = 0
        sql_count = 0
        
        for py_file in python_files[:30]:
            content = safe_read_file(py_file).lower()
            if 'import pandas' in content or 'from pandas' in content or 'pd.' in content:
                pandas_count += 1
            if 'sql' in content or 'query(' in content or 'execute(' in content or 'cursor' in content:
                sql_count += 1
        
        if pandas_count >= 3:
            signals.append("pandas usage")
        
        if sql_count >= 2:
            signals.append("SQL usage")
        
        if pandas_count >= 5 or (pandas_count >= 3 and sql_count >= 1):
            return True
        
        req_file = os.path.join(repo_path, 'requirements.txt')
        if os.path.exists(req_file):
            de_libs = ['pandas', 'pyspark', 'dask', 'airflow', 'prefect', 'sqlalchemy', 'psycopg2', 'mysql-connector']
            if check_dependencies_file(req_file, de_libs):
                return True
        
        return len(signals) >= 2
    except Exception as e:
        warnings.append(f"Error detecting data_engineering: {str(e)}")
        return False


def detect_skill_tags(repo_path):
    """
    Detect skill tags in a Git repository.
    
    Args:
        repo_path: Path to the Git repository
        
    Returns:
        dict with skill tags (boolean values) and warnings list
    """
    warnings = []
    
    if not repo_path:
        warnings.append("Repository path is empty")
        return _get_default_output(warnings)
    
    if not os.path.exists(repo_path):
        warnings.append(f"Repository path does not exist: {repo_path}")
        return _get_default_output(warnings)
    
    if not os.path.isdir(repo_path):
        warnings.append(f"Repository path is not a directory: {repo_path}")
        return _get_default_output(warnings)
    
    try:
        backend = detect_backend(repo_path, warnings)
        frontend = detect_frontend(repo_path, warnings)
        machine_learning = detect_machine_learning(repo_path, warnings)
        competitive_programming = detect_competitive_programming(repo_path, warnings)
        devops = detect_devops(repo_path, warnings)
        data_engineering = detect_data_engineering(repo_path, warnings)
        
        return {
            "backend": backend,
            "frontend": frontend,
            "machine_learning": machine_learning,
            "competitive_programming": competitive_programming,
            "devops": devops,
            "data_engineering": data_engineering,
            "warnings": warnings
        }
    except Exception as e:
        warnings.append(f"Critical error in detect_skill_tags: {str(e)}")
        return _get_default_output(warnings)


def _get_default_output(warnings):
    """Return default output dictionary with safe fallback values."""
    return {
        "backend": False,
        "frontend": False,
        "machine_learning": False,
        "competitive_programming": False,
        "devops": False,
        "data_engineering": False,
        "warnings": warnings
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python layer_skill_detector.py <repo_path>")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    result = detect_skill_tags(repo_path)
    
    print(json.dumps(result, indent=2))
