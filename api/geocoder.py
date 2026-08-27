import requests


NOMINATIM_URL = (
    "https://nominatim.openstreetmap.org/search"
)


def search_location(query):

    headers = {
        "User-Agent":
            "Mauksh-Kundali/1.0"
    }

    params = {
        "q": query,
        "format": "json",
        "addressdetails": 1,
        "limit": 5
    }

    response = requests.get(
        NOMINATIM_URL,
        params=params,
        headers=headers,
        timeout=10
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
                address.get(
                    "city"
                )
                or address.get(
                    "town"
                )
                or address.get(
                    "village"
                ),

            "state":
                address.get(
                    "state"
                ),

            "country":
                address.get(
                    "country"
                ),

            "country_code":
                address.get(
                    "country_code"
                )

        })

    return locations
