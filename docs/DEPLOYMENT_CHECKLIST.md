# Rank Tracker - Production Deployment Checklist

## Pre-Deployment

- [ ] Install dependencies: `pip install aiohttp beautifulsoup4`
- [ ] Run tests: `python examples_rank_tracker.py`
- [ ] Validate installation: `python setup_rank_tracker.py --validate`
- [ ] Review documentation: Read `RANK_TRACKER_README.md`
- [ ] Test with 5-10 keywords before scaling

## Core Setup

- [ ] Create configuration: `python setup_rank_tracker.py --domain example.com`
- [ ] Generate keywords file with target keywords
- [ ] Test CLI: `python rank_tracker.py check example.com keyword1`
- [ ] Verify database creation: `ls -la rank_tracker.db`
- [ ] Check database schema: `sqlite3 rank_tracker.db ".schema"`

## Optimization

- [ ] Set appropriate delays based on proxy availability
  - [ ] No proxies: `min_delay=5.0, max_delay=10.0`
  - [ ] With proxies: `min_delay=2.0, max_delay=5.0`
- [ ] Add proxies if tracking 50+ keywords: `--proxies http://... http://...`
- [ ] Test with different search engines: `--engines google bing`
- [ ] Verify proxy rotation working: Check logs for different proxy IPs

## Scheduling

- [ ] **Linux/macOS - Cron**:
  ```bash
  0 0 * * * /usr/bin/python3 /opt/auditor/rank_tracker.py check example.com keyword1 keyword2
  ```
  - [ ] Test cron job: `*/1 * * * * echo "test" >> /tmp/cron_test.log`
  - [ ] Verify permissions: `chmod +x rank_tracker.py`

- [ ] **Windows - Task Scheduler**:
  ```batch
  schtasks /create /tn "RankTracker" /tr "python C:\auditor\rank_tracker.py check example.com keywords" /sc daily /st 00:00
  ```
  - [ ] Test task manually
  - [ ] Verify logs

- [ ] **Python - APScheduler**:
  ```python
  scheduler.add_job(daily_check, 'cron', hour=0, minute=0)
  ```
  - [ ] Test schedule locally first
  - [ ] Set up log file

- [ ] **Docker - Container**:
  ```bash
  docker run -v rank_data:/data rank-tracker check example.com keywords
  ```
  - [ ] Test Docker image build
  - [ ] Verify volume mounting
  - [ ] Test with docker-compose

## FastAPI Integration

- [ ] Import router: `from rank_tracker_api import router`
- [ ] Add to app: `app.include_router(router)`
- [ ] Test endpoints locally:
  - [ ] `POST /api/rank-tracker/check`
  - [ ] `GET /api/rank-tracker/history/{domain}/{keyword}`
  - [ ] `GET /api/rank-tracker/trend/{domain}/{keyword}`
  - [ ] `GET /api/rank-tracker/alerts/{domain}`
- [ ] Verify API documentation at `/docs`
- [ ] Test with Postman/curl

## Database

- [ ] Backup strategy:
  - [ ] Daily backups to separate location
  - [ ] Test restore procedure
  - [ ] Set retention policy (keep last 30 days)

- [ ] PostgreSQL migration (if high volume):
  - [ ] Set up PostgreSQL server
  - [ ] Migrate schema and data
  - [ ] Update connection string

- [ ] Database optimization:
  - [ ] Run `VACUUM` weekly
  - [ ] Run `ANALYZE` for statistics
  - [ ] Add indexes for common queries

## Monitoring & Logging

- [ ] Set up logging:
  ```python
  logging.basicConfig(
      level=logging.INFO,
      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
      handlers=[
          logging.FileHandler('rank_tracker.log'),
          logging.StreamHandler()
      ]
  )
  ```
  - [ ] Log file rotation set up
  - [ ] Retention policy configured

- [ ] Error tracking:
  - [ ] Set up Sentry/error logging
  - [ ] Configure alerts for failures
  - [ ] Create incident response plan

- [ ] Performance monitoring:
  - [ ] Monitor request times
  - [ ] Track success/failure rates
  - [ ] Alert on anomalies

## Alerts & Notifications

- [ ] Email alerts:
  - [ ] Set up email service (SMTP/SendGrid)
  - [ ] Template for alert emails
  - [ ] Test email delivery

- [ ] Slack notifications:
  - [ ] Set up Slack webhook
  - [ ] Template for Slack messages
  - [ ] Test webhook

- [ ] Alert thresholds configured:
  - [ ] CRITICAL: Lost top 10 position
  - [ ] WARNING: Dropped 5+ positions
  - [ ] INFO: Improved 5+ positions

## Testing

- [ ] Unit tests written for custom code
- [ ] Integration tests for API endpoints
- [ ] Load test with target volume:
  - [ ] 10 keywords: ~2 minutes
  - [ ] 50 keywords: ~10 minutes
  - [ ] 100 keywords: ~20 minutes

- [ ] Test edge cases:
  - [ ] Keywords not ranking
  - [ ] CAPTCHA challenges
  - [ ] Network timeouts
  - [ ] Proxy failures

## Security

- [ ] API endpoints:
  - [ ] Add authentication (API key, OAuth)
  - [ ] Rate limiting enabled
  - [ ] Input validation

- [ ] Data protection:
  - [ ] Encrypt sensitive data at rest
  - [ ] Use HTTPS for API
  - [ ] Secure database credentials

- [ ] Access control:
  - [ ] Limit to admin users
  - [ ] Audit logging enabled
  - [ ] IP whitelisting (if needed)

## Performance Tuning

- [ ] Request rate optimization:
  - [ ] Baseline response time: ___ ms
  - [ ] Target response time: ___ ms
  - [ ] Number of concurrent requests: ___

- [ ] Database performance:
  - [ ] Query times acceptable
  - [ ] Index coverage verified
  - [ ] Connection pooling configured

- [ ] Memory usage:
  - [ ] Baseline: ___ MB
  - [ ] Peak: ___ MB
  - [ ] Optimization if needed

## Documentation

- [ ] README with setup instructions
- [ ] API documentation (auto-generated at `/docs`)
- [ ] Troubleshooting guide created
- [ ] Runbook for common tasks
- [ ] Configuration examples documented
- [ ] Backup/restore procedures documented

## Deployment

- [ ] Development environment ✓
- [ ] Staging environment:
  - [ ] Deploy code
  - [ ] Run integration tests
  - [ ] Verify 24-hour operation
- [ ] Production environment:
  - [ ] Deploy code
  - [ ] Monitor for 48 hours
  - [ ] Track key metrics

## Post-Deployment

- [ ] Monitor logs daily for first week
- [ ] Check alert emails/Slack notifications
- [ ] Verify data accuracy with manual spot checks
- [ ] Get user feedback
- [ ] Address any issues
- [ ] Document lessons learned

## Maintenance Plan

- [ ] Database maintenance schedule:
  - [ ] Weekly: VACUUM, ANALYZE
  - [ ] Monthly: Backup verification
  - [ ] Quarterly: Performance review

- [ ] Dependency updates:
  - [ ] Monthly: Check for updates
  - [ ] Quarterly: Update patch versions
  - [ ] Semi-annually: Review major updates

- [ ] Code review:
  - [ ] Monthly: Review logs and errors
  - [ ] Quarterly: Code quality review
  - [ ] Semi-annually: Architecture review

## Rollback Plan

- [ ] Previous version backed up
- [ ] Rollback procedure documented
- [ ] Test rollback in staging
- [ ] Team trained on rollback
- [ ] Estimated rollback time: ___ minutes

## Success Metrics

Track these after deployment:

- [ ] Daily check success rate: ___% (target: 95%+)
- [ ] Average check time: ___ minutes (target: <20 min for 100 kw)
- [ ] Database growth rate: ___ MB/day
- [ ] Alert accuracy: ___% (target: 99%+)
- [ ] False positive rate: ___% (target: <5%)

## Stakeholder Communication

- [ ] Team trained on new system
- [ ] Users informed of new features
- [ ] Documentation shared
- [ ] Support contact established
- [ ] Feedback mechanism set up

## Sign-Off

| Role | Name | Date | Sign |
|------|------|------|------|
| Developer | __________ | ______ | ____ |
| QA | __________ | ______ | ____ |
| DevOps | __________ | ______ | ____ |
| Manager | __________ | ______ | ____ |

## Post-Deployment Notes

```
Date deployed: __________________
Version: __________________
Notable issues: __________________
Performance observations: __________________
Next review date: __________________
```

---

## Quick Commands Reference

```bash
# Check keywords
python rank_tracker.py check example.com "keyword1" "keyword2"

# View history
python rank_tracker.py history example.com "keyword1"

# View alerts
python rank_tracker.py alerts example.com

# Database maintenance
sqlite3 rank_tracker.db "VACUUM;"
sqlite3 rank_tracker.db "ANALYZE;"

# Backup
cp rank_tracker.db rank_tracker.db.backup.$(date +%Y%m%d)

# View logs
tail -f rank_tracker.log

# Validate setup
python setup_rank_tracker.py --validate
```

## Emergency Procedures

### If tracking stops
1. Check logs: `tail -f rank_tracker.log`
2. Verify database: `sqlite3 rank_tracker.db "SELECT COUNT(*) FROM rank_records;"`
3. Test connectivity: `curl https://www.google.com`
4. Restart service: `systemctl restart rank_tracker`

### If CAPTCHA blocking occurs
1. Add more proxies to rotation
2. Increase delay: `min_delay=5.0, max_delay=10.0`
3. Switch search engines temporarily
4. Manual restart after 1 hour

### If database grows too large
1. Export old data: `sqlite3 rank_tracker.db ".mode csv" ".headers on" "SELECT * FROM rank_records WHERE timestamp < '2026-01-01';" > old_records.csv`
2. Archive to separate database
3. Delete old records: `DELETE FROM rank_records WHERE timestamp < date('now', '-90 days');`
4. Optimize: `VACUUM;`

---

**Deployment Sign-Off Date**: ________________

**Deployed By**: ________________

**Contact for Issues**: ________________
