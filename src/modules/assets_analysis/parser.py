import requests
import datetime

from bs4 import BeautifulSoup

def fetch_from_coinmarketcap(coin, days):
    url = f"https://coinmarketcap.com/currencies/{coin}/historical-data/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"[-] Ошибка загрузки CoinMarketCap для {coin}: {response.status_code}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", class_="cmc-table")

    if not table:
        print(f"[-] Не найдена таблица на CoinMarketCap для {coin}")
        return None

    rows = table.find_all("tr")[1:days + 1]
    prices = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        date_str = cols[0].text.strip()
        high_price = cols[2].text.strip().replace("$", "").replace(",", "")

        try:
            date_obj = datetime.datetime.strptime(date_str, "%b %d, %Y")
            high_price = float(high_price)
            prices.append((date_obj, high_price))
        except ValueError:
            continue

    return prices if prices else None

def fetch_current_price_from_coinmarketcap(coin):
    url = f"https://coinmarketcap.com/currencies/{coin}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"[-] Ошибка загрузки CoinMarketCap для {coin}: {response.status_code}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    price_tag = soup.find("div", class_="priceValue")

    if price_tag:
        price_text = price_tag.text.strip().replace("$", "").replace(",", "")
        try:
            return float(price_text)
        except ValueError:
            return None

    print(f"[-] Не удалось получить текущую цену с CoinMarketCap для {coin}")
    return None
