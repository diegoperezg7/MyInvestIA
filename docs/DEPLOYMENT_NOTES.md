# Deployment Notes

## Production Deployment

### Backend

#### Environment Variables

Required:
```bash
# Supabase (optional, for persistence)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# API Keys (at least one required)
FINNHUB_API_KEY=your-key
NEWSAPI_KEY=your-key
GDELT_API_KEY=your-key
REDDIT_CLIENT_ID=your-key
REDDIT_CLIENT_SECRET=your-key

# AI Services (optional)
GROQ_API_KEY=your-key
OPENAI_API_KEY=your-key

# Telegram (optional, for alerts)
TELEGRAM_BOT_TOKEN=your-token
TELEGRAM_CHAT_ID=your-chat-id
```

#### Running with Docker

```bash
docker build -t myinvestia-backend ./backend
docker run -d -p 8000:8000 --env-file .env myinvestia-backend
```

#### Running with Docker Compose

```bash
docker-compose up -d backend
```

### Frontend

#### Environment Variables

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

#### Building for Production

```bash
cd frontend
npm run build
npm start
```

#### Docker Deployment

```bash
docker build -t myinvestia-frontend ./frontend
docker run -d -p 3000:3000 --env-file .env.local myinvestia-frontend
```

## Free Tier Operation

MyInvestIA is designed to work with free tier data providers:

### Data Providers (Free)

| Provider | Limit | Setup |
|----------|-------|-------|
| Finnhub | 60 calls/min | Get free API key |
| NewsAPI | 100 calls/day | Get free API key |
| GDELT | 15 min delay | No key required |
| Reddit | 60 calls/min | OAuth setup |

### AI Services (Free)

| Service | Model | Limit |
|---------|-------|-------|
| Groq | llama-3.1-70b | High throughput |
| Cerebras | llama-3.1-70b | Very high |

## Supabase Setup (Optional)

For persistent data storage:

1. Create a Supabase project
2. Run migrations (see `supabase/migrations/`)
3. Configure environment variables

### Schema

The database uses:
- `users` - User management
- `holdings` - Portfolio positions
- `theses` - Investment thesis
- `journal_entries` - Decision log
- `inbox_items` - AI insights

## Monitoring

### Health Checks

```bash
GET /health
```

Returns:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-01-01T00:00:00Z"
}
```

### Metrics

The backend exposes Prometheus metrics at `/metrics` when enabled:

```bash
METRICS_ENABLED=true
```

## Security

### API Authentication

All endpoints require JWT authentication:
```
Authorization: Bearer <jwt_token>
```

### CORS

Configure allowed origins:
```bash
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### Rate Limiting

Rate limiting is per-IP and configurable:
```bash
RATE_LIMIT_PER_MINUTE=60
```

## Troubleshooting

### 504 Gateway Timeout

- Increase timeout in nginx/docker-compose
- Check API key rate limits
- Reduce number of assets scanned

### Memory Issues

- In-memory store grows with usage
- Restart periodically or use Supabase
- Limit cached assets

### Data Not Persisting

- Check Supabase credentials
- Verify table permissions
- Check Supabase logs

## Backup & Recovery

### Manual Backup

```bash
# Export data from Supabase
supabase db dump > backup.sql
```

### Restore

```bash
# Restore data to Supabase
psql $DATABASE_URL -f backup.sql
```

## Performance Tuning

### Backend

- Use uvicorn with workers: `uvicorn app.main:app --workers 4`
- Enable caching: `CACHE_TTL=300`
- Tune connection pools

### Frontend

- Enable Next.js caching
- Use CDN for static assets
- Optimize images

## Scaling

### Horizontal Scaling

The backend is stateless and can be scaled horizontally:
- Use a load balancer
- Share Supabase for data
- Use Redis for caching

### Vertical Scaling

Recommended resources:
- Minimum: 2 CPU, 2GB RAM
- Recommended: 4 CPU, 4GB RAM
