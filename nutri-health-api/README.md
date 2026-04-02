# NutriHealth API

FastAPI backend for the NutriHealth mobile application - providing food scanning and nutritional analysis for children aged 7-12.

## Features

- **Food Image Analysis**: Upload food images for AI-powered nutritional analysis
- **Gemini AI Integration**: Uses Google's Gemini 1.5 Flash for food recognition
- **Smart Caching**: PostgreSQL-based caching with 1-day TTL for performance
- **Child-Friendly Responses**: Tailored language and health assessments for children
- **RESTful API**: Well-documented endpoints with OpenAPI/Swagger
- **Production Ready**: Configured for deployment on Render.com

## Tech Stack

- **Framework**: FastAPI 0.115.0
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI**: Google Gemini 1.5 Flash
- **Image Processing**: Pillow
- **Server**: Uvicorn (ASGI)

## Project Structure

```
nutri-health-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── database.py          # Database configuration
│   ├── models/
│   │   ├── __init__.py
│   │   └── cache.py         # Cache model
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── scan.py          # Pydantic schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini.py        # Gemini AI integration
│   │   └── cache.py         # Cache service
│   └── routers/
│       ├── __init__.py
│       └── scan.py          # Scan endpoints
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker configuration
├── render.yaml             # Render.com deployment config
├── .env.example           # Environment variables template
└── README.md              # This file
```

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or use Render.com managed database)
- Google Gemini API key

### Local Development

1. **Clone the repository**
   ```bash
   cd nutri-health-api
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and configure at minimum:
   - `DATABASE_URL`: PostgreSQL connection string
   - `GEMINI_API_KEY`: Your Gemini API key

   The default startup behavior is to create tables only. Seed import is disabled by default.

5. **Run the server**
   ```bash
   uvicorn app.main:app --reload
   ```

   The API will be available at `http://localhost:8000`

6. **Access API documentation**
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

### Startup Initialization

- On startup, the service always runs database table initialization (`create_all`).
- It does not import seed data unless `SEED_ON_STARTUP=true` is set in `.env`.
- If you need the initial seed data, update the startup config, restart the service, and the seed will run once for that `SEED_KEY`.

## API Endpoints

### POST /scan

Upload a food image for analysis.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: `file` (image file, JPEG or PNG, max 5MB)

**Response:**
```json
{
  "food_name": "Chocolate Chip Cookie",
  "nutritional_info": {
    "calories": 150,
    "carbohydrates": 20.0,
    "protein": 2.0,
    "fats": 7.0
  },
  "health_assessment": "This cookie is high in sugar and fats...",
  "alternatives": [
    {
      "name": "Oatmeal Raisin Cookie",
      "description": "Contains oats which provide fiber..."
    }
  ]
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "nutrihealth-api"
}
```

### GET /admin/cleanup-cache

Manually trigger cache cleanup (removes expired entries).

**Response:**
```json
{
  "status": "success",
  "entries_deleted": 5
}
```

## Database Schema

### scan_cache Table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| image_hash | String(64) | SHA-256 hash of image (unique) |
| response_data | JSONB | Cached scan results |
| created_at | DateTime | Creation timestamp |
| expires_at | DateTime | Expiration timestamp (TTL: 1 day) |

## Deployment

### Render.com

1. **Push code to GitHub**
   ```bash
   git add .
   git commit -m "Deploy to Render"
   git push origin main
   ```

2. **Create Render account**
   - Go to [render.com](https://render.com)
   - Sign up or log in

3. **Deploy using Blueprint**
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Select the repository and branch
   - Render will automatically detect `render.yaml`

4. **Set environment variables**
   - Go to your web service dashboard
   - Navigate to "Environment"
   - Add `GEMINI_API_KEY` (the only manual env var needed)

5. **Monitor deployment**
   - Check the "Logs" tab for deployment progress
   - Once deployed, access your API at the provided URL

### Environment Variables

Required:
- `DATABASE_URL`: Automatically set by Render.com
- `GEMINI_API_KEY`: Set manually in Render dashboard

Optional:
- `CORS_ORIGINS`: Comma-separated list of allowed origins
- `ENVIRONMENT`: `development` or `production`

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### Code Quality

```bash
# Format code
black app/

# Lint code
flake8 app/

# Type checking
mypy app/
```

### Database Migrations

Currently using auto-migration on startup. For production, consider using Alembic:

```bash
# Install Alembic
pip install alembic

# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

## Troubleshooting

### Database Connection Issues

- Ensure PostgreSQL is running
- Check `DATABASE_URL` is correctly formatted
- Verify network connectivity to database

### Gemini API Errors

- Verify `GEMINI_API_KEY` is set correctly
- Check API quota limits
- Review Gemini API status page

### Cache Not Working

- Check database connection
- Verify `scan_cache` table exists
- Review application logs for errors

## Performance Optimization

- **Caching**: Results cached for 1 day to reduce API calls
- **Connection Pooling**: SQLAlchemy pool configured for 5-15 connections
- **Image Optimization**: Images converted to RGB before processing
- **Async Processing**: FastAPI async endpoints for better concurrency

## Security

- File type validation (JPEG, PNG only)
- File size limits (5MB maximum)
- SQL injection protection via SQLAlchemy
- CORS configuration for allowed origins
- Environment-based secrets management

## License

Proprietary - NutriHealth Project

## Support

For issues and questions, please contact the development team.
