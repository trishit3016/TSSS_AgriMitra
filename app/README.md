# AgriChain Harvest Optimizer - Backend

FastAPI backend for the AgriChain Harvest Optimizer XAI Trust Engine.

## Project Structure

```
app/
├── __init__.py           # Package initialization
├── main.py               # FastAPI application entry point
├── config/               # Configuration and settings
│   ├── __init__.py
│   └── settings.py       # Environment variable management
├── models/               # Pydantic models
│   ├── __init__.py
│   ├── requests.py       # Request models
│   └── responses.py      # Response models
├── agents/               # LangGraph agents (to be implemented)
├── services/             # External service integrations (to be implemented)
└── utils/                # Utility functions (to be implemented)

tests/
├── __init__.py
├── test_main.py          # Application tests
└── test_models.py        # Model validation tests
```

## Setup

1. Install Python 3.11+
2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

5. Run the application:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

## API Endpoints

- `GET /` - Root endpoint with API information
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)

## Testing

Run tests with pytest:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

## Development

Format code with black:
```bash
black app/ tests/
```

Lint with ruff:
```bash
ruff check app/ tests/
```
