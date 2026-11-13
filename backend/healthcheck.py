"""Container health check: succeeds as soon as the web server answers.

Any HTTP status counts as "alive" (a 400 only means that 127.0.0.1 is not in
ALLOWED_HOSTS); a refused connection or a timeout fails the check.
"""

import os
import sys
import urllib.error
import urllib.request

url = f"http://127.0.0.1:{os.environ.get('PORT', '8000')}/"
try:
    urllib.request.urlopen(url, timeout=4)
except urllib.error.HTTPError:
    pass
except Exception as error:  # noqa: BLE001 - any other failure means "down"
    print(f"health check failed: {error}", file=sys.stderr)
    sys.exit(1)
