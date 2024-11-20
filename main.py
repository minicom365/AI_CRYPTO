import argparse
import os
import time
from datetime import datetime, timedelta
import json
from tqdm import tqdm
import yaml
from dotenv import load_dotenv
import pyupbit
import openai
from translate import Translator
import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.traceback import install
from auto_update import do_update
from logger import LogManager
from indicator import add_indicators
from crawler import *

# 환경 변수 로드
load_dotenv()

# 설정 파일 로드
with open("config.yaml", "r", encoding='utf-8') as file:
    config = yaml.safe_load(file)

# 상수 정의
TEST_FLAG = False  # 테스트 모드 플래그
UPBIT_ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY")
UPBIT_SECRET_KEY = os.getenv("UPBIT_SECRET_KEY")
CURRENCY = "BTC"  # 거래할 티커
UNIT_CURRENCY = "KRW"
TICKER = UNIT_CURRENCY + "-" + CURRENCY

# 로그 설정
install(show_locals=True)
log_manager = LogManager(loggerName="__main__", configPath='logger.yaml')
logger = log_manager.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s:\n%(message)s\n')

rich_handler = RichHandler(level=logging.INFO, rich_tracebacks=True)
rich_handler.setLevel(logging.INFO)
logger.addHandler(rich_handler)

file_handler = logging.FileHandler('log', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 거래 이력 저장
trade_history = []


while True:
    # Upbit Client 초기화
    upbit = pyupbit.Upbit(UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY)
    response = upbit.get_balances()
    if 'error' in response:
        logger.error(response['error'])
        if response['error']['name']:
            ip = requests.get('https://checkip.amazonaws.com').text.strip()
            logger.info(f"ip가 등록되지 않았습니다: {ip}")
        logger.info("30초 추가대기")
        time.sleep(30)
    else:
        break


def calculate_realized_profit(ticker=None):
    """보유 중인 암호화폐의 실현 손익을 계산합니다.

    Args:
        balances (list): 보유 중인 암호화폐의 잔고 정보.
        ticker (str, optional): 특정 암호화폐의 티커. 지정되지 않으면 모든 암호화폐에 대해 계산.

    Returns:
        float: 실현 손익 퍼센티지
    """
    total_profit = 0.0

    # 현재가 조회
    balances = get_balances()

    for balance_info in balances:
        n_ticker = f"{balance_info['unit_currency']}-{balance_info['currency']}"

        # 특정 티커만 계산할 경우
        if ticker and n_ticker != ticker:
            continue

        avg_buy_price = float(balance_info['avg_buy_price'])  # 평균 매입 단가
        quantity = float(balance_info['balance'] + balance_info['locked'])  # 잔고
        # print(n_ticker, avg_buy_price, quantity)
        try:
            current_price = get_current_price(n_ticker)  # 현재가
        except:
            current_price = 0

        # 실현 손익 계산
        if quantity > 0 and avg_buy_price > 0:
            # 현재 가격 대비 평균 매수가의 등락률 계산
            price_change_percentage = ((current_price - avg_buy_price) / avg_buy_price)

            # 등락률에 기반한 실현 손익
            total_profit += price_change_percentage

    return total_profit


def fetch_data(ticker, interval="day", count=30):
    """주어진 티커와 설정으로 차트 데이터를 가져옵니다."""
    return pyupbit.get_ohlcv(ticker, count=count, interval=interval)


def get_balances(ticker=None) -> dict:
    """보유 자산 및 잔고 조회"""
    if ticker:
        return {
            "KRW": upbit.get_balance("KRW"),
            ticker: upbit.get_balance(ticker)
        }
    else:
        return upbit.get_balances()


def get_orderboot(ticker):
    pyupbit.get_orderbook(ticker)


def filter_json(json_string):
    start_index = json_string.find('{')
    end_index = json_string.rfind('}') + 1
    return json_string[start_index:end_index].replace("\n", "")


def get_ai():
    base_url = config["ai"].get("base_url")
    if base_url == 'openrouter':
        ai = openai
        ai.api_key = os.getenv("OPENROUTER_API_KEY")
        ai.base_url = "https://openrouter.ai/api/v1/"
    else:
        ai = openai
        ai.api_key = os.getenv("OPENAI_API_KEY")
        ai.base_url = base_url

    return ai


def translate(text):
    try:
        params = {
            'q': text,
            'source': 'en',
            'target': 'ko',
            'format': 'text'
        }

        # API 호출
        response = requests.post('https://libretranslate.com/translate', data=params)

        # 번역 결과 출력
        return response.json()['translatedText']
    except:
        return text


def get_chance(ticker):
    return upbit.get_chance(ticker)


def ai_make_message(ticker: str, balances: dict):
    daily_data = fetch_data(ticker)
    shortly_data = fetch_data(ticker, interval=config["shortly_data_interval"], count=config['shortly_data_count'])
    daily_data, shortly_data = list(map(add_indicators, [daily_data, shortly_data]))
    data_combined = {
        "daily_data": daily_data.to_json(),
        f"shortly_data({config['shortly_data_interval']})": shortly_data.to_json()
    }
    bid_fee, ask_fee = [get_chance(ticker)[x] for x in ['bid_fee', 'ask_fee']]
    return json.dumps({
        "ticker": ticker,
        "now_time": str(datetime.now().astimezone()),
        "now_price": get_current_price(ticker),
        "data": data_combined,
        "balances": balances,
        "trade_history": trade_history,
        #  "resent_reflection": "WIP",
        #  "resent_reflection": reflection on recent transactions,
        "realized_profit": calculate_realized_profit(ticker),
        "orderbook": get_orderboot(ticker),
        "fee": {"bid_fee": bid_fee, "ask_fee": ask_fee},
        "resent_news": get_recent_news(20, api_key=os.getenv("CRYPTOPANIC_API_KEYS")),
        "FGI": get_fear_greed_index(5)})


def ai_Query(instruct: str, messages: str) -> dict:
    """AI에 차트 데이터 및 잔고를 전달하여 매매 결정을 요청합니다."""
    ai = get_ai()

    def chkerr(response):
        if hasattr(response, "error"):
            message = response.error['message']
            if type(message) == dict:
                message = message.get("error", {}).get("message")
            if "Rate limit exceeded" in message:
                remaining, limit, reset = [response.headers.get(
                    f"x-ratelimit-{x}") for x in ["remaining", "limit", "reset"]]
                logger.error(f"AI 매매 결정 중 오류 발생: {message}")
                logger.error(f"AI 사용량 만료: {remaining}/{limit}")
                logger.error(f"다음 갱신: {reset}")
            else:
                logger.error("AI 매매 결정 중 오류 발생: %s", message if message else response.error['message'])
            raise StopIteration()
        elif response.choices:
            return response.choices[0].message.content

    try:
        logger.debug(messages)
        response = ai.chat.completions.create(
            model=config["ai"]["model"],
            messages=[{"role": "user", "content": f"{messages}\n\n{instruct}"}]
        )

        return json.loads(filter_json(chkerr(response)))

    except StopIteration:
        return None
    except Exception as e:
        if "Error code: 429" in str(e):
            # 이부분 어떻게 에러가 발생하는지 명확치않음
            chkerr(response)
        elif e != "No active exception to reraise":
            logger.error(f"AI 매매 결정 중 오류 발생: {e}")
        return None


def execute_trade(ticker, decision, target_price, percent, balances):
    """AI의 매매 결정과 퍼센트를 기반으로 거래를 실행합니다."""
    if TEST_FLAG:
        logger.info("### 테스트 모드 - 실제 거래는 실행되지 않습니다 ###")
        return

    krw_balance = balances.get("KRW", 0)
    asset_balance = balances.get(ticker, 0)
    trade_amount = 0

    if decision == "buy":
        if krw_balance <= 5000:
            logger.warning("### 거래 실패 - 충분한 자금이 없습니다 ###")
            return
        trade_amount = min(krw_balance * percent * 0.9995, krw_balance)

    elif decision == "sell":
        est_krw_value = asset_balance * percent * get_current_price(ticker)
        if est_krw_value <= 5000:
            logger.warning("### 거래 실패 - 충분한 자산이 없습니다 ###")
            return
        trade_amount = asset_balance * percent

    elif decision == "hold":
        logger.info("### 보유 유지 ###")
        return

    return place_order(ticker, decision, trade_amount, target_price)


def place_order(ticker: str, order_type: str, amount: float, price: float = None):
    """주문 유형에 따라 지정가 또는 시장가 주문을 실행합니다. 최소 주문 가능 금액을 확인합니다."""
    try:
        trade_trans = {
            "buy": "bid",
            "sell": "ask"
        }
        # 주문 가능 정보 조회 및 최소 주문 금액 확인
        chance_info = upbit.get_chance(ticker)
        if not chance_info:
            raise ValueError("주문 가능 정보 조회에 실패했습니다.")

        # 판매시 오류 발생 wip
        # min_order_amount = float(chance_info['market'][trade_trans[order_type]]['min_total'])
        # if amount < min_order_amount:
        #     raise ValueError(f"{order_type} 주문 금액 {amount}가 최소 금액 {min_order_amount}보다 작습니다.")

        # 주문 실행
        if order_type == "buy":
            response = (upbit.buy_market_order(ticker, amount) if price == None
                        else upbit.buy_limit_order(ticker, price, amount / price))
        elif order_type == "sell":
            response = (upbit.sell_market_order(ticker, amount) if price == None
                        else upbit.sell_limit_order(ticker, price, amount))
        else:
            raise ValueError("올바르지 않은 주문 유형입니다.")

        return response

    except Exception as e:
        logger.error(f"주문 처리 중 오류 발생: {e}")
        Console().print_exception(show_locals=True)
        return None


def log_trade(order_response, reason=None):
    if order_response:
        """거래 기록을 생성하고 로그를 작성합니다."""
        trade_trans = {
            "bid": "buy",
            "ask": "sell"
        }
        trade_type = trade_trans.get(order_response['side'])  # 'ask' 또는 'bid'
        record = {
            'type': trade_type,
            'state': order_response['state'],
            'uuid': order_response['uuid'],
            'price': order_response['price'],
            'quantity': order_response['volume'],  # 거래 수량
            'reason': reason
        }

        trade_history.append(record)  # 거래 기록을 저장합니다.
        logger.info(f"### 거래 기록 생성: {record} ###")  # 로그 작성
    else:
        logger.warning(f"### 거래 실패: {order_response} ###")  # 로그 작성


def get_last_buy_trade():
    """마지막 구매 거래를 조회합니다."""
    return next((trade for trade in reversed(trade_history) if trade['type'] == 'buy'), None)


def get_current_price(ticker):
    """현재 가격을 조회합니다."""
    return pyupbit.get_current_price(ticker)


def get_fluctuation_rate(now, to): return (to - now) / now * 100


def translate(message: str):
    result = Translator(to_lang="ko").translate(message)
    return result if not 'MYMEMORY WARNING:' in result else message


def main():
    logger.debug("디버깅으로 기록")
    """주기적으로 매매 결정을 실행합니다 (모든 보유 자산을 매도할 때까지)"""
    first_run = True
    logger.info(f"### 사용 AI 모델: {config["ai"]["model"]} ###")

    while True:
        if os.getenv("AUTO_UPDATE"):
            do_update()
        try:
            results = None
            next_trade_wait = 0
            balances = get_balances(TICKER)
            if balances[TICKER] == 0:
                if first_run:
                    logger.info("### 아직 코인을 구매하지 않았습니다 ###")
                else:
                    logger.info("### 모든 자산 매도 완료 ###")
            logger.info(f"### 현시점 수익률: {calculate_realized_profit(TICKER) * 100}% ###")

            logger.info("### 데이터 수집 시작 ###")
            message = ai_make_message(TICKER, balances)
            logger.info("### 데이터 수집 완료 ###")

            logger.info("### AI 쿼리 시도 ###")
            ai_answer = ai_Query(config["ai"]["instruct"], message)
            if ai_answer:
                price = get_current_price(TICKER)
                decision = ai_answer.get("decision")
                target_price = ai_answer.get("target_price", None) or price
                reason = translate(ai_answer.get("reason"))
                percent = ai_answer.get("percent", 1.0)
                next_trade_wait = ai_answer.get("next_trade_wait", 0)
                next_trade_time = (datetime.now() + timedelta(minutes=next_trade_wait)).strftime("%H:%M:%S")
                alert_price = {f: ai_answer.get(f"alert_price_{f}") for f in ["low", "high"]}
                alert_price_rate = {f: get_fluctuation_rate(price, alert_price[f]) for f in ["low", "high"]}

                logger.info(f"### AI 결정: {decision.upper()} ###", )
                logger.info(f"### 현재 시세: {price} ###")
                logger.info(f"### 목표 금액: {target_price} ###")
                logger.info(f"### 이유: {reason} ###")
                logger.info(f"### 거래 비율: {percent * 100}% ###")
                logger.info(f"### 다음 거래 대기 시간: {next_trade_wait}분 ({next_trade_time}) ###")
                logger.info(f"### 대기 취소 금액(하한가): {alert_price['low']} ({alert_price_rate['low']:.2f}%) ###")
                logger.info(f"### 대기 취소 금액(상한가): {alert_price['high']} ({alert_price_rate['high']:.2f}%) ###")

                if decision == "buy":
                    first_run = not first_run
                    target_price = min(target_price, price)
                elif decision == "sell":
                    target_price = max(target_price, price)
                if not TEST_FLAG and decision != 'hold':
                    results = execute_trade(TICKER, decision, target_price, percent, balances)
                    logger.debug(results)
                    log_trade(results, reason)
                    if not results:
                        next_trade_wait = None
            else:
                logger.error("### 결정 실패 - AI 응답 없음 ###")

        except Exception as E:
            Console().print_exception(show_locals=True)

        last_trade_time = time.time()
        wait_time = 60 * next_trade_wait if next_trade_wait else 60
        pbar = tqdm(total=wait_time, unit='s')
        pbar.set_description(f'다음 거래까지 대기:')

        while True:
            try:
                price = get_current_price(TICKER)

                # AI 응답에 따른 가격 경고
                if ai_answer:
                    alert_price_high = ai_answer.get("alert_price_high")
                    alert_price_low = ai_answer.get("alert_price_low")

                    if price > alert_price_high:
                        logger.warning(f'### 가격 급상승 감지 --  ### {price} > {alert_price_high}')
                        break
                    elif price < alert_price_low:
                        logger.warning(f'### 가격 급하락 감지 --  ### {price} < {alert_price_low}')
                        break

                remaining_time = (last_trade_time + wait_time) - time.time()
                if remaining_time > 0:
                    elapsed_time = time.time() - last_trade_time
                    pbar.n = int(elapsed_time)
                    pbar.refresh()
                    time.sleep(1)  # 1초 대기 후 다음 반복
                else:
                    break
            except:
                pass

        pbar.close()  # Progress bar 닫기


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-t", "--ticker", type=str, help="Set the ticker symbol")
        args = parser.parse_args()

        if args.ticker:
            if not "-" in args.ticker:
                args.ticker = f"{UNIT_CURRENCY}-{args.ticker}"
            TICKER = args.ticker.upper()

        main()
    except KeyboardInterrupt:
        print("프로그램이 종료되었습니다.")
