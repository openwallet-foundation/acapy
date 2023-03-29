import sys
from urllib.request import urlopen
from urllib.error import URLError, HTTPError


def check_url(url):
    try:
        with urlopen(url) as response:
            return response.status == 200
    except HTTPError as e:
        print(f"Error: {e}")
        return False
    except URLError as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python healthcheck.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    is_healthy = check_url(url)
    sys.exit(0 if is_healthy else 1)
