# Mwmbl Posting System

A multi-platform posting system that automatically collects activities from Matrix, GitHub, and Mwmbl stats API, then posts daily updates to Mastodon and X, and weekly summaries to a GitHub Pages blog.

## Features

- **Data Collection**: Automatically collects activities from:
  - Matrix room messages (#mwmbl:matrix.org)
  - GitHub repositories (mwmbl organization)
  - Mwmbl statistics API

- **Content Processing**: 
  - Filters newsworthy activities
  - Formats content for different platforms
  - Uses Claude AI for weekly summaries

- **Multi-Platform Publishing**:
  - Daily posts to Mastodon and X/Twitter
  - Weekly blog posts to GitHub Pages
  - Platform-specific formatting and character limits

- **Robust Architecture**:
  - PostgreSQL database for activity tracking
  - Comprehensive error handling and logging
  - Duplicate detection and rate limiting
  - Docker deployment ready

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   Processors     │    │   Publishers    │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ Matrix Collector│───▶│ Content Filter   │───▶│ Mastodon        │
│ GitHub Collector│    │ Content Formatter│    │ X/Twitter       │
│ Stats Collector │    │ AI Summarizer    │    │ Blog (GitHub)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │   PostgreSQL Database   │
                    │   - Activities          │
                    │   - Posts               │
                    │   - Scheduling          │
                    └─────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.13+
- PostgreSQL database
- API credentials for all platforms

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd post
```

2. Install dependencies:
```bash
pip install -e .
```

3. Copy and configure environment variables:
```bash
cp config/.env.example .env
# Edit .env with your API credentials
```

4. Initialize the database:
```bash
python main.py init-db
```

5. Test connections:
```bash
python main.py test-connections
```

## Configuration

### Environment Variables

Copy `config/.env.example` to `.env` and configure:

#### Database
```env
DATABASE_URL=postgresql://user:password@localhost:5432/post_db
```

#### Matrix
```env
MATRIX_HOMESERVER=https://matrix.org
MATRIX_USER_ID=@your_username:matrix.org
MATRIX_ACCESS_TOKEN=your_matrix_access_token
MATRIX_ROOM_ID=!mwmbl:matrix.org
```

#### GitHub
```env
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_ORG=mwmbl
```

#### Mastodon
```env
MASTODON_INSTANCE_URL=https://your.mastodon.instance
MASTODON_ACCESS_TOKEN=your_mastodon_access_token
```

#### X/Twitter
```env
X_API_KEY=your_x_api_key
X_API_SECRET=your_x_api_secret
X_ACCESS_TOKEN=your_x_access_token
X_ACCESS_TOKEN_SECRET=your_x_access_token_secret
X_BEARER_TOKEN=your_x_bearer_token
```

#### Claude AI
```env
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### API Credentials Setup

#### Matrix
1. Create a Matrix account
2. Get access token from Element → Settings → Help & About → Advanced

#### GitHub
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Create token with `repo` and `read:org` permissions

#### Mastodon
1. Go to your Mastodon instance → Preferences → Development
2. Create new application with `read` and `write` permissions

#### X/Twitter
1. Apply for Twitter Developer account
2. Create app and get API keys and tokens

#### Anthropic Claude
1. Sign up at https://console.anthropic.com/
2. Get API key from the dashboard

## Usage

### CLI Commands

```bash
# Initialize database
python main.py init-db

# Test all connections
python main.py test-connections

# Collect activities (last 24 hours)
python main.py collect

# Run daily posting
python main.py daily-post

# Run weekly posting
python main.py weekly-post

# View statistics
python main.py stats --days 7

# Clean up temporary files
python main.py cleanup
```

### Scheduling

For production deployment, use the provided scripts:

#### Daily Posting (run at 9 AM)
```bash
python scripts/daily_post.py
```

#### Weekly Posting (run on Mondays at 10 AM)
```bash
python scripts/weekly_post.py
```

## Docker Deployment

### Build and Run

```bash
# Build image
docker build -t mwmbl-post .

# Run with environment file
docker run --env-file .env mwmbl-post python main.py daily-post
```

### Dokku Deployment

1. Create Dokku app:
```bash
dokku apps:create mwmbl-post
```

2. Set environment variables:
```bash
dokku config:set mwmbl-post DATABASE_URL=postgresql://...
# Set all other environment variables
```

3. Deploy:
```bash
git remote add dokku dokku@your-server:mwmbl-post
git push dokku main
```

4. Set up cron jobs:
```bash
# Daily posting at 9 AM
dokku cron:set mwmbl-post "0 9 * * *" "python scripts/daily_post.py"

# Weekly posting on Mondays at 10 AM
dokku cron:set mwmbl-post "0 10 * * 1" "python scripts/weekly_post.py"
```

## Development

### Project Structure

```
post/
├── src/
│   ├── collectors/          # Data collection from sources
│   ├── processors/          # Content filtering and formatting
│   ├── publishers/          # Platform publishing
│   ├── scheduler/           # Task orchestration
│   └── storage/            # Database models and management
├── config/                 # Configuration and settings
├── scripts/               # Deployment scripts
├── main.py               # CLI interface
├── Dockerfile           # Docker configuration
└── README.md           # This file
```

### Adding New Collectors

1. Create new collector in `src/collectors/`
2. Inherit from `BaseCollector`
3. Implement `collect()` method
4. Add to `TaskScheduler`

### Adding New Publishers

1. Create new publisher in `src/publishers/`
2. Inherit from `BasePublisher`
3. Implement required methods
4. Add to `TaskScheduler`

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src
```

### Code Quality

```bash
# Format code
black src/ config/ scripts/ main.py

# Sort imports
isort src/ config/ scripts/ main.py

# Type checking
mypy src/
```

## Monitoring and Logging

- Logs are written to both console and file (`post.log`)
- Log rotation: 10MB files, 30 days retention
- Health checks available for Docker deployment
- Statistics tracking for all posting activities

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL is running
   - Verify DATABASE_URL is correct
   - Ensure database exists

2. **API Authentication Errors**
   - Verify all API credentials are correct
   - Check token permissions and expiry
   - Test individual connections

3. **Matrix Connection Issues**
   - Ensure Matrix room ID is correct
   - Check access token has room permissions
   - Verify homeserver URL

4. **Blog Publishing Fails**
   - Check GitHub repository permissions
   - Verify blog repository URL
   - Ensure Git credentials are configured

### Debug Mode

Run with verbose logging:
```bash
python main.py -v <command>
```

### Getting Help

- Check logs in `post.log`
- Run connection tests: `python main.py test-connections`
- View recent statistics: `python main.py stats`

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
