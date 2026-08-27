import time
import threading
import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

REQUEST_GAP_SECONDS = 1.1

_cache = {}
_cache_lock = threading.Lock()
_last_request_at = 0.0


def _get_cache(query):
    key = query.strip().casefold()

    with _cache_lock:
        value = _cache.get(key)

        if value is None:
            return None

        return [dict(item) for item in value]


def _set_cache(query, value):
    key = query.strip().casefold()

    with _cache_lock:
        _cache[key] = [
            dict(item)
            for item in value
        ]


def _wait_for_rate_limit():

    global _last_request_at

    with _cache_lock:

        now = time.monotonic()

        wait = (
            REQUEST_GAP_SECONDS
            - (now - _last_request_at)
        )

        if wait > 0:
            time.sleep(wait)

        _last_request_at = time.monotonic()


def search_location(query):

    query = query.strip()

    if not query:
        return []


    # --------------------------------------------------------
    # CACHE
    # --------------------------------------------------------

    cached = _get_cache(query)

    if cached is not None:
        return cached


    # --------------------------------------------------------
    # NOMINATIM
    # --------------------------------------------------------

    headers = {
        "User-Agent":
            "Mauksh-Kundali/1.1 (+https://mauksh.com)"
    }

    params = {
        "q": query,
        "format": "json",
        "addressdetails": 1,
        "limit": 5
    }


    _wait_for_rate_limit()


    response = requests.get(
        NOMINATIM_URL,
        params=params,
        headers=headers,
        timeout=15
    )


    # --------------------------------------------------------
    # 429 RETRY
    # --------------------------------------------------------

    if response.status_code == 429:

        retry_after = response.headers.get(
            "Retry-After",
            "2"
        )

        try:
            retry_seconds = min(
                float(retry_after),
                10.0
            )

        except ValueError:
            retry_seconds = 2.0


        time.sleep(
            max(
                retry_seconds,
                1.1
            )
        )


        _wait_for_rate_limit()


        response = requests.get(
            NOMINATIM_URL,
            params=params,
            headers=headers,
            timeout=15
        )


    response.raise_for_status()


    results = response.json()


    locations = []


    for item in results:

        address = item.get(
            "address",
            {}
        )


        locations.append({

            "display_name":
                item.get(
                    "display_name"
                ),

            "latitude":
                float(
                    item["lat"]
                ),

            "longitude":
                float(
                    item["lon"]
                ),

            "city":
                address.get("city")
                or address.get("town")
                or address.get("village")
                or address.get("municipality"),

            "state":
                address.get("state"),

            "country":
                address.get("country"),

            "country_code":
                address.get(
                    "country_code"
                )

        })


    # --------------------------------------------------------
    # SAVE CACHE
    # --------------------------------------------------------

    _set_cache(
        query,
        locations
    )


    return locations