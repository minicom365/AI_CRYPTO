import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import random
import time

from main import ai_Query, ai_make_message


def init(ticker, trade_history, realized_profit, chart_data, ai_instruct):
    st.set_page_config(page_title="AI 기반 자동 거래 시각화 대시보드", layout="wide")
    st.sidebar.header("거래 정보 설정")

    st.header("실시간 가격 확인")

    balances = generate_random_balances()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("잔고 정보")
        balances_placeholder = st.empty()
        display_balances(balances, balances_placeholder)

    with col2:
        pie_chart_placeholder = st.empty()

    realized_profit_placeholder = st.empty()
    realized_profit_placeholder.metric("실현 수익률 (%)", f"{realized_profit * 100:.2f}")

    st.header("AI 매매 결정")
    if st.button("AI 매매 결정을 요청"):
        message = ai_make_message(ticker, balances)
        decision = ai_Query(ai_instruct, message)
        if decision:
            display_ai_decision(decision)
        else:
            st.error("AI 응답 없음")

    st.header("과거 거래 내역")
    trade_history_placeholder = st.empty()
    display_trade_history(trade_history_placeholder, trade_history)

    st.header("차트 데이터")
    line_chart_placeholder = st.empty()
    line_chart_placeholder.line_chart(chart_data["close"])

    return pie_chart_placeholder, line_chart_placeholder, trade_history_placeholder, balances_placeholder, realized_profit_placeholder


@st.fragment(run_every="1s")
def update_prices(line_chart_placeholder, chart_data, balances, balances_placeholder):
    # 시세 업데이트
    price = random.uniform(500000, 600000)
    chart_data["close"].append(price)
    line_chart_placeholder.line_chart(chart_data["close"], use_container_width=True)

    # 평가금액 업데이트
    update_total_value(balances, price, balances_placeholder)


def update_data(
        trade_history, pie_chart_placeholder, trade_history_placeholder, balances_placeholder,
        realized_profit_placeholder, chart_data):
    # 잔고 업데이트
    balances = generate_random_balances()
    price = chart_data["close"][-1]  # 가장 최근 시세 사용
    update_total_value(balances, price, balances_placeholder)

    update_pie_chart(balances, pie_chart_placeholder)
    display_balances(balances, balances_placeholder)

    new_trade = generate_random_trade()
    trade_history.append(new_trade)
    display_trade_history(trade_history_placeholder, trade_history)

    realized_profit = random.uniform(0, 0.1)
    realized_profit_placeholder.metric("실현 수익률 (%)", f"{realized_profit * 100:.2f}")

    return trade_history, balances


def update_total_value(balances, price, balances_placeholder):
    # 시세와 보유량을 곱해 평가금액 동적 계산
    for balance in balances:
        if balance["currency"] == "BTC":
            balance["total_value"] = balance["balance"] * price
    display_balances(balances, balances_placeholder)


def generate_random_balances():
    return [
        {"currency": "KRW", "balance": round(random.uniform(100000, 1000000), 2), "locked": 0, "avg_buy_price": 0, "unit_currency": "KRW"},
        {"currency": "BTC", "balance": round(random.uniform(0, 1), 4), "locked": 0, "avg_buy_price": round(random.uniform(30000000, 60000000), 2), "unit_currency": "KRW"},
    ]


def generate_random_trade():
    trade_type = random.choice(["buy", "sell"])
    price = round(random.uniform(500000, 600000), 2)
    amount = round(random.uniform(0.01, 0.5), 4)
    return {"trade_type": trade_type, "price": price, "amount": amount, "time": pd.Timestamp.now()}


def display_balances(balances, placeholder):
    translated_data = []
    for balance in balances:
        translated_data.append({
            "자산": balance.get('currency', "-"),
            "보유 수량": float(balance.get('balance', "-")),
            "출금 가능 수량": float(balance.get('locked', "-")),
            "평균 매수 가격 (KRW)": float(balance.get('avg_buy_price', "-")),
            "단위 통화": balance.get('unit_currency', "-"),
            "총 가치 (KRW)": float(balance.get('total_value', 0)) if balance['currency'] == 'BTC' else 0
        })

    balances_df = pd.DataFrame(translated_data)
    placeholder.table(balances_df)


def display_ai_decision(decision):
    st.json(decision)
    trade_decision = decision.get("decision")
    target_price = decision.get("target_price")
    reason = decision.get("reason")
    percent = decision.get("percent", 1.0) * 100

    # AI 결정 정보 표시
    st.metric("결정", trade_decision)
    st.metric("목표 금액", f"{target_price:,} KRW")
    st.metric("이유", reason)
    st.metric("거래 비율", f"{percent:.2f} %")


def display_trade_history(trade_history_placeholder, trade_history):
    # 거래 내역을 DataFrame으로 변환하여 표시
    if trade_history:
        trade_history_df = pd.DataFrame(trade_history)
        trade_history_df['시간'] = pd.to_datetime(trade_history_df['time'])
        trade_history_df = trade_history_df[['시간', 'trade_type', 'price', 'amount']]
        trade_history_df.columns = ['시간', '거래 유형', '가격 (KRW)', '수량']

        # 표 형식으로 표시
        trade_history_placeholder.table(trade_history_df)
    else:
        trade_history_placeholder.write("거래 내역이 없습니다.")


def update_pie_chart(balances, pie_chart_placeholder):
    labels = [balance['currency'] for balance in balances]
    values = [float(balance['balance']) for balance in balances]

    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.3, hoverinfo="label+percent+value")])
    fig.update_traces(hoverinfo='label+percent+value', textinfo='label+value')  # 호버 시 정보 표시
    fig.update_layout(title="잔고 비율", margin=dict(t=50, b=50, l=50, r=50), template="plotly_dark")

    # pie_chart_placeholder에 업데이트
    pie_chart_placeholder.plotly_chart(fig, use_container_width=True)  # 고유 키 제거


if __name__ == "__main__":
    ticker = "KRW-BTC"
    trade_history = [{"trade_type": "buy", "price": 500000, "amount": 0.1, "time": "2024-11-08 12:00"}]
    realized_profit = 0.05
    chart_data = {"close": [500000, 510000, 520000, 530000, 540000]}
    ai_instruct = {"instruction": "매매 결정을 내려주세요"}

    pie_chart_placeholder, line_chart_placeholder, trade_history_placeholder, balances_placeholder, realized_profit_placeholder = init(
        ticker, trade_history, realized_profit, chart_data, ai_instruct)

    balances = generate_random_balances()  # 초기 balances 정의

    while True:
        trade_history, balances = update_data(
            trade_history, pie_chart_placeholder, trade_history_placeholder,
            balances_placeholder, realized_profit_placeholder, chart_data)
        time.sleep(10)
