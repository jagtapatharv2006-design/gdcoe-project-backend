# HPPS System - High-Pay Potential Score

A comprehensive system for calculating High-Pay Potential Scores (HPPS) for students based on their coding profiles, competitive programming ratings, Git activity, and project complexity.

## Features

- **Code Analysis**: Analyzes Git repositories for code quality, complexity, and project structure
- **Skill Detection**: Automatically detects skills (backend, frontend, ML, DevOps, etc.) from code
- **Git Analytics**: Extracts commit history, activity patterns, and consistency metrics
- **Rating Integration**: Fetches Codeforces and LeetCode ratings
- **HPPS Calculation**: Calculates comprehensive HPPS scores with four dimensions:
  - **AD (Algorithmic Depth)**: Competitive programming and problem-solving skills
  - **EAP (Execution & Application Power)**: Real-world project experience
  - **CCL (Consistency & Career Longevity)**: Long-term commitment and consistency
  - **LA (Leverage & Adaptability)**: Modern tech usage and adaptability
- **Job Matching**: Matches students to job postings using AI-powered keyword extraction
- **REST API**: Full REST API for managing students, jobs, and analyses
- **Async Processing**: Celery-based background task processing
- **Database**: SQLAlchemy ORM with support for SQLite (dev) and PostgreSQL (prod)

## Architecture

```
Student GitHub URL 
  → Git Manager (clone/update)
  → Code Analyzer (metrics)
  → Skill Detector (tags)
  → Git Analytics (activity)
  → HPPS Calculator (final score)
  → Database (store results)
```

## Quick Start

### Prerequisites

- Python 3.11+
- Git
- Redis (for Celery, optional)
- PostgreSQL (optional, SQLite works for development)

### Installation

1. **Clone the repository** (if applicable)

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. **Initialize the database**:
```bash
# Database tables are auto-created on first run
# Or use Alembic for migrations:
alembic upgrade head
```

5. **Start services**:

   **Development (manual)**:
   ```bash
   # Terminal 1: Redis (optional, falls back to sync if not running)
   redis-server
   
   # Terminal 2: Celery worker (optional)
   celery -A tasks worker --loglevel=info
   
   # Terminal 3: FastAPI server
   uvicorn app:app --reload
   ```

   **Production (Docker)**:
   ```bash
   docker-compose up -d
   ```

6. **Access the API**:
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## Usage Examples

### Create a Student

```bash
curl -X POST http://localhost:8000/students \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "github_url": "https://github.com/johndoe/myrepo",
    "cf_username": "johndoe",
    "lc_username": "johndoe"
  }'
```

### Trigger Analysis

```bash
curl -X POST http://localhost:8000/students/1/analyze?async_mode=false
```

### Get HPPS Score

```bash
curl http://localhost:8000/students/1/score
```

### Create a Job Posting

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Backend Developer",
    "description": "Looking for Python backend developer with FastAPI experience."
  }'
```

### Get Job Matches

```bash
curl http://localhost:8000/jobs/1/matches
```

## Configuration

Key configuration options in `.env`:

- `DATABASE_URL`: Database connection string (SQLite or PostgreSQL)
- `REDIS_URL`: Redis connection for Celery
- `GEMINI_API_KEY`: Required for job keyword extraction
- `GITHUB_TOKEN`: Optional, for private repository access
- `REPO_STORAGE_PATH`: Where to store cloned repositories
- `ANALYSIS_TIMEOUT`: Maximum time for analysis (seconds)

## API Endpoints

### Students
- `POST /students` - Create student
- `GET /students/{id}` - Get student details
- `GET /students` - List all students
- `PUT /students/{id}` - Update student
- `DELETE /students/{id}` - Delete student
- `GET /students/{id}/score` - Get HPPS score
- `POST /students/{id}/analyze` - Trigger analysis

### Jobs
- `POST /jobs` - Create job posting
- `GET /jobs/{id}` - Get job details
- `GET /jobs/{id}/matches` - Get matched students
- `POST /jobs/{id}/match` - Trigger job matching

### Tasks
- `GET /tasks/{task_id}` - Get task status

### Health
- `GET /health` - Health check

## Project Structure

```
hpps_system/
├── app.py                 # FastAPI application
├── models.py              # SQLAlchemy models
├── database.py            # Database connection and DAOs
├── pipeline.py            # Analysis pipeline orchestration
├── git_manager.py         # Git repository management
├── scrapers.py            # Rating scrapers (CF/LC)
├── tasks.py               # Celery tasks
├── celery_config.py       # Celery configuration
├── schemas.py             # Pydantic schemas
├── config.py              # Configuration management
├── logger.py              # Logging setup
├── utils.py               # Utility functions
├── function.py            # HPPS calculation engine
├── layer0_code_analyzer.py  # Code analysis
├── layer_skill_detector.py  # Skill detection
├── job_matching_layer.py    # Job matching
├── alembic/               # Database migrations
├── tests/                 # Test files
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose setup
└── README.md              # This file
```

## Development

### Running Tests

```bash
pytest tests/
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Code Quality

The system uses optional tools for better analysis:
- `radon` - Cyclomatic complexity analysis
- `pylint` - Code quality checks
- `ruff` - Fast Python linter

## Error Handling

The system is designed to be error-proof:
- All analysis functions have comprehensive fallbacks
- Missing data is handled gracefully with default values
- Network failures (API calls, Git operations) are handled with retries
- Database operations use transactions with rollback on errors

## Limitations

- LeetCode rating is not publicly available via API (requires authentication)
- Analysis requires Git repositories (not suitable for non-Git projects)
- Code analysis focuses primarily on Python projects (other languages have basic support)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

[Add your license here]

## Support

For issues and questions, please open an issue on the repository.
