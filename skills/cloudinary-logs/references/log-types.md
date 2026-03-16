# Available Log Types

Common log files found per instance in `s3://cloudinary-logs/{service}/{date}/{instance-id}/`:

- `production.YYYYMMDD-HH.log.gz` - Main Rails production logs
- `error-log-*.log.gz` - Error logs
- `nrt_cache_syncer.*.log.gz` - NRT cache sync logs
- `redis_syncer.*.log.gz` - Redis synchronization logs
- `seget-log.*.log.gz` - Seget logs
- `permission_enforcement.*.log.gz` - Permission enforcement logs
- `capsule.*.log.gz` - Capsule logs
- `passenger.log.gz` - Passenger web server logs
- `syslog.gz` - System logs

## Notes

- Production logs are large (400-500MB compressed per hour)
- Analysis is performed on decompressed logs
- Downloaded files are stored in the current directory
