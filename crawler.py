import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def init_driver():
    """
    Chrome 웹드라이버를 초기화하고 반환합니다.
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def get_fear_greed_index(limit: int = 1) -> dict:
    """
    공포탐욕지수 API를 호출하고 결과를 반환합니다.
    """
    url = 'https://api.alternative.me/fng/'
    params = {
        'limit': limit,
        'format': 'json'
    }
    response = requests.get(url, params=params)
    data = response.json()

    if 'data' in data:
        index_data = data['data'][0]
        return {
            'value': index_data['value'],
            'status': index_data['value_classification'],
            'last_update': index_data['timestamp']
        }
    else:
        print("Error: Unable to fetch Fear & Greed Index.")
        return None


def get_recent_news(num: int = 5, ticker: str = None, api_key: str = None) -> list[str]:
    """
    비트코인 관련 최신 뉴스를 API 키 유무에 따라 가져옵니다.
    """
    if api_key:
        # Cryptopanic API 사용
        url = 'https://cryptopanic.com/api/v1/posts/'
        params = {
            'auth_token': api_key,
            'filter': 'news',
            'currencies': ticker,
            'kind': 'news',
            'public': 'true',
            'limit': num
        }
        response = requests.get(url, params=params)
        data = response.json()

        if 'results' in data:
            return [
                {
                    'title': article['title'],
                    'link': article['url'],
                    'published_time': article['published_at']
                }
                for article in data['results']
            ]
        else:
            print("Error: Unable to fetch news from Cryptopanic API.")
            return None
    else:
        # Selenium을 사용한 웹 스크래핑
        try:
            # Chrome 웹드라이버 초기화
            driver = init_driver()
            url = 'https://cryptopanic.com/news/'
            driver.get(url)
            news_list = []
            list_num = 0

            while True:
                list_num += 1
                WebDriverWait(
                    driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, f'div.news > div:nth-child({list_num}) > div > a > span.title-text')))
                article = driver.find_element(By.CSS_SELECTOR, f'div.news > div:nth-child({list_num})')

                if len(news_list) >= num:
                    break

                try:
                    title = article.find_element(By.CLASS_NAME, 'title-text').text.strip()
                    link = article.find_element(By.TAG_NAME, 'a').get_attribute('href')
                    published_time = article.find_element(By.TAG_NAME, 'time').get_attribute('datetime')
                except Exception:
                    continue

                news_list.append({
                    'title': title,
                    'link': link,
                    'published_time': published_time
                })
        except Exception as e:
            print("Error: Unable to fetch news via web scraping:", e)
            return None
        finally:
            driver.quit()

        return news_list


# 실행 코드
if __name__ == '__main__':
    # 공포탐욕지수 출력
    fgi = get_fear_greed_index()
    print("공포탐욕지수:")
    print(f"현재 지수: {fgi['value']}")
    print(f"상태: {fgi['status']}")
    print(f"마지막 업데이트: {fgi['last_update']}")
    print("\n")

    # 비트코인 관련 최신 뉴스 출력
    print("비트코인 관련 최신 뉴스:")
    news_list = get_recent_news()
    for news in news_list:
        print("\n")
        print(f"제목: {news['title']}")
        print(f"발행 시간: {news['published_time']}")
        print(f"링크: {news['link']}")
