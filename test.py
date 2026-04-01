import requests

proxies = {
  "http": "http://proxy1:mypass@192.168.56.1:8080",
}

resp = requests.get(f"https://www.google.com/search?q=nike", proxies=proxies, timeout=15)
print(resp.status_code, resp.text[:200])