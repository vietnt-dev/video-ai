import httpx
import os

key = "Puhbx2afuFuFvyTWy90fJNDMeSt7QGHMrLI4TsYBHC3UjVpB2Wu71tQJ"

headers = {
    "Authorization": key,
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
}
params = {
    "query": "nature",
    "per_page": 1,
}

response = httpx.get("https://api.pexels.com/videos/search", headers=headers, params=params)
print(response.status_code)
print(response.text)
