PROXY_HOST = 'microcorruption.com'
PROXY_URL = 'https://{}'.format(PROXY_HOST)

REDIS_PREFIX = 'microcorruption_'
COOKIE_KEY = REDIS_PREFIX + 'cookies'
CSRF_KEY = REDIS_PREFIX + 'csrf'
REFRESH_KEY = REDIS_PREFIX + 'refresh'

GDB_HOST = 'localhost'
GDB_PORT = 1338
