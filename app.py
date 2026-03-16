import streamlit as st
import math

st.set_page_config(
    page_title="테슬라 모델Y 할부 시뮬레이터",
    page_icon="",
    layout="wide",
)

st.title("테슬라 Model Y 할부 구매 시뮬레이터")
st.caption("테슬라 공식 가격 기준 · longrange.gg 보조금 기준 · 삼성카드 다이렉트 오토")

# ─── 상수 ──────────────────────────────────────────────────────
TRIMS = {
    "Model Y Premium RWD": {
        "key": "rwd",
        "price": 49_990_000,
        "gov": 170,
        "spec": "후륜구동 · 505km · 0→100 4.8초",
    },
    "Model Y Premium Long Range AWD": {
        "key": "lr",
        "price": 59_990_000,
        "gov": 210,
        "spec": "사륜구동 · 최고속 201km/h",
    },
}

OPTIONS = {
    "도색": {
        "Stealth Grey (기본 포함)": 0,
        "Pearl White Multi-Coat (+128.6만)": 1_286_000,
        "Deep Blue Metallic (+128.6만)": 1_286_000,
        "Glacier Blue (+128.6만)": 1_286_000,
        "Crimson Red (+128.6만)": 1_286_000,
        "Quicksilver (+128.6만)": 1_286_000,
    },
    "휠": {
        "19인치 사이클론 (기본 포함)": 0,
        "20인치 헬릭스 2.0 (+257.1만)": 2_571_000,
    },
    "인테리어": {
        "All Black (기본 포함)": 0,
        "Black & White (+128.6만)": 1_286_000,
    },
}

REGIONS = {
    "서울특별시":    {"rwd": 51,  "lr": 63},
    "경기도 (평균)": {"rwd": 65,  "lr": 78},
    "인천광역시":    {"rwd": 60,  "lr": 72},
    "부산광역시":    {"rwd": 68,  "lr": 82},
    "대구광역시":    {"rwd": 70,  "lr": 84},
    "광주광역시":    {"rwd": 75,  "lr": 90},
    "기타 지역":     {"rwd": 80,  "lr": 96},
}

def fmt_man(won: float) -> str:
    v = round(won / 10_000, 1)
    return f"{v:,.1f}만원"

def calc_monthly(principal: float, months: int, annual_rate: float):
    if principal <= 0 or months <= 0:
        return 0.0, 0.0
    if annual_rate == 0:
        return principal / months, 0.0
    r = annual_rate / 100 / 12
    monthly = principal * r * math.pow(1 + r, months) / (math.pow(1 + r, months) - 1)
    total_interest = monthly * months - principal
    return monthly, total_interest

# ─── session_state 초기화 ──────────────────────────────────────
for key, default in [
    ("prev_trim",   "Model Y Premium RWD"),
    ("prev_region", "서울특별시"),
    ("gov_sub",     170),
    ("local_sub",   51),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─── 레이아웃 ──────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:

    # ── 트림 선택 ──────────────────────────────────────────────
    st.subheader("트림 선택")
    trim_name = st.radio(
        "트림",
        list(TRIMS.keys()),
        label_visibility="collapsed",
        format_func=lambda x: (
            f"{x}  —  {TRIMS[x]['price']//10_000:,}만원  |  {TRIMS[x]['spec']}"
        ),
    )
    trim_key = TRIMS[trim_name]["key"]
    base_price = TRIMS[trim_name]["price"]

    use_custom = st.toggle("출고가 직접 입력", value=False)
    if use_custom:
        custom_man = st.number_input(
            "출고가 (만원)",
            min_value=0,
            max_value=50_000,
            value=base_price // 10_000,
            step=10,
        )
        base_price = custom_man * 10_000

    # ── 옵션 선택 ──────────────────────────────────────────────
    st.subheader("옵션")
    opt_total = 0
    for opt_name, opt_choices in OPTIONS.items():
        chosen = st.selectbox(opt_name, list(opt_choices.keys()))
        opt_total += opt_choices[chosen]

    car_price = base_price + opt_total
    st.info(
        f"옵션 합계: **+{fmt_man(opt_total)}**  |  출고가 합계: **{fmt_man(car_price)}**"
    )

    # ── 보조금 ─────────────────────────────────────────────────
    st.subheader("보조금")
    st.caption("longrange.gg · 2026-03-14 기준")

    with st.expander("트림별 보조금 참고 (서울 개인 기준)"):
        st.markdown(
            """
| 모델 | 국가 보조금 | 지방(서울) | 합계 |
|------|:-----------:|:---------:|:----:|
| Model Y Premium RWD | 170만원 | 51만원 | 221만원 |
| Model Y Premium Long Range | 210만원 | 63만원 | 273만원 |
"""
        )

    region = st.selectbox("지역", list(REGIONS.keys()))

    # 트림 또는 지역 변경 시 슬라이더 자동 리셋
    trim_changed = (trim_name != st.session_state.prev_trim)
    region_changed = (region != st.session_state.prev_region)

    if trim_changed or region_changed:
        st.session_state.gov_sub = TRIMS[trim_name]["gov"]
        st.session_state.local_sub = REGIONS[region][trim_key]
        st.session_state.prev_trim = trim_name
        st.session_state.prev_region = region
        st.rerun()

    gov_sub = st.slider(
        "국가 보조금 (만원)",
        min_value=0,
        max_value=500,
        step=5,
        key="gov_sub",
    )
    local_sub = st.slider(
        "지방 보조금 (만원)",
        min_value=0,
        max_value=300,
        step=1,
        key="local_sub",
    )

    total_sub_won = (gov_sub + local_sub) * 10_000
    net_price = max(0, car_price - total_sub_won)
    st.success(
        f"실구매가: **{fmt_man(net_price)}** (보조금 {fmt_man(total_sub_won)} 차감)"
    )

    # ── 할부 조건 ──────────────────────────────────────────────
    st.subheader("할부 조건")
    st.caption("삼성카드 다이렉트 오토 기준")

    down_pct = st.slider("선수금 비율 (%)", 0, 50, 20, step=5)
    months = st.select_slider("할부 기간", options=[24, 36, 48, 60], value=60)
    annual_rate = st.slider("연 할부금리 (%)", 0.0, 12.0, 2.3, step=0.1)

    down_amt = round(net_price * down_pct / 100)
    principal = net_price - down_amt

    # ── 월 유지비 ──────────────────────────────────────────────
    st.subheader("월 유지비")
    ins    = st.slider("보험료 (만원/월)", 5, 30, 12, step=1) * 10_000
    charge = st.slider("충전비 (만원/월)", 2, 15,  7, step=1) * 10_000
    misc   = st.slider("기타 유지비 (만원/월)", 0, 10, 2, step=1) * 10_000


# ─── 우측: 결과 ────────────────────────────────────────────────
with col_right:
    st.subheader("결과 요약")

    monthly_loan, total_interest = calc_monthly(principal, months, annual_rate)
    monthly_principal = principal / months if months > 0 else 0
    monthly_interest  = monthly_loan - monthly_principal
    monthly_maint     = ins + charge + misc
    grand_total       = monthly_loan + monthly_maint

    # 핵심 지표
    c1, c2, c3 = st.columns(3)
    c1.metric("실구매가",  fmt_man(net_price),  f"보조금 -{fmt_man(total_sub_won)}")
    c2.metric("선수금",    fmt_man(down_amt),   f"{down_pct}%")
    c3.metric("할부 원금", fmt_man(principal))

    st.divider()

    # 월 납입 상세
    st.markdown("#### 월 납입 상세")
    rate_label = "무이자" if annual_rate == 0 else f"연 {annual_rate:.1f}%"

    details = [
        ("원금 할부금",           fmt_man(monthly_principal)),
        (f"이자 ({rate_label})",  fmt_man(monthly_interest) if total_interest > 0 else "0원"),
        ("보험료",                fmt_man(ins)),
        ("충전비",                fmt_man(charge)),
        ("기타 유지비",           fmt_man(misc)),
    ]
    for label, value in details:
        a, b = st.columns([2, 1])
        a.markdown(f"<span style='color:gray'>{label}</span>", unsafe_allow_html=True)
        b.markdown(f"**{value}**")

    st.divider()

    a, b = st.columns([2, 1])
    a.markdown("### 월 총 비용")
    b.markdown(f"### {fmt_man(grand_total)}")

    if total_interest > 0:
        st.caption(f"전체 기간 총 이자: {fmt_man(total_interest)}")
    else:
        st.caption("전체 기간 총 이자: 없음 (무이자)")

    st.divider()

    # 기간별 비교 표
    st.markdown("#### 할부 기간별 비교")
    rows = []
    for m in [24, 36, 48, 60]:
        ml, ti = calc_monthly(principal, m, annual_rate)
        rows.append({
            "기간":    f"{m}개월",
            "월 할부금": fmt_man(ml),
            "월 총비용": fmt_man(ml + monthly_maint),
            "총 이자":  fmt_man(ti) if ti > 0 else "없음",
        })
    st.table(rows)

    # 5년 총 보유 비용
    st.markdown("#### 5년 총 보유 비용")
    total_60 = grand_total * 60 + down_amt
    st.info(
        f"선수금 {fmt_man(down_amt)} + 월 {fmt_man(grand_total)} x 60개월\n\n"
        f"**총 = {fmt_man(total_60)}** (유지비 포함)"
    )

    st.caption("본 시뮬레이터는 참고용이며 실제 조건은 테슬라·삼성카드에서 확인하세요.")
