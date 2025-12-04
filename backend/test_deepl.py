import requests

DEEPL_API_KEY = "TU_API_KEY_AQUÍ"

url = "https://api-free.deepl.com/v2/translate"

params = {
    "auth_key": DEEPL_API_KEY,
    "text": "Hello world",
    "target_lang": "ES"
}

response = requests.post(url, data=params)
print(response.status_code)
print(response.json())
