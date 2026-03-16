"""
테슬라 Model Y 할부 구매 시뮬레이터
- 모든 슬라이더에 숫자 직접 입력 칸 병행 제공
- 테슬라 공식 가격 기준 (2026년 3월)
- longrange.gg 보조금 기준 (2026-03-14)
- 17개 광역시도 지방 보조금 + 취등록비 계산 포함
"""

import streamlit as st
import math
import pandas as pd

st.set_page_config(
    page_title="테슬라 모델Y 할부 시뮬레이터",
    page_icon="",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────
# 상수 데이터
# ─────────────────────────────────────────────────────────────────

TRIMS = {
    "Model Y Premium RWD": {
        "key": "rwd",
        "price": 49_990_000,
        "gov": 170,
        "spec": "후륜구동 ·최고속 201km/h· 주행가능 거리 400km · 제로백 5.9초",
    },
    "Model Y Premium Long Range AWD": {
        "key": "lr",
        "price": 59_990_000,
        "gov": 210,
        "spec": "사륜구동 · 최고속 201km/h· 주행가능 거리 505km · 제로백 4.8초",
    },
}

OPTIONS = {
    "도색": {
        "Stealth Grey (기본 포함)": 0,
        "Pearl White Multi-Coat (+128.6만)": 1_286_000,
        "Diamond Black (+192.9만)": 1_929_000,        
        "Glacier Blue (+192.9만)": 1_929_000,
        "Crimson Red (+275.9만)": 2_759_000,
        "Quicksilver (+275.9만)": 2_759_000,
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
    "서울특별시":      {"rwd": 51,  "lr": 63,  "bond_pct": 12.0},
    "부산광역시":      {"rwd": 68,  "lr": 84,  "bond_pct":  4.0},
    "대구광역시":      {"rwd": 70,  "lr": 84,  "bond_pct":  4.0},
    "인천광역시":      {"rwd": 60,  "lr": 72,  "bond_pct":  5.0},
    "광주광역시":      {"rwd": 75,  "lr": 90,  "bond_pct":  5.0},
    "대전광역시":      {"rwd": 60,  "lr": 72,  "bond_pct":  4.0},
    "울산광역시":      {"rwd": 70,  "lr": 84,  "bond_pct":  4.0},
    "세종특별자치시":  {"rwd": 80,  "lr": 96,  "bond_pct":  4.0},
    "경기도 (평균)":   {"rwd": 65,  "lr": 78,  "bond_pct":  9.0},
    "강원특별자치도":  {"rwd": 100, "lr": 120, "bond_pct":  4.0},
    "충청북도":        {"rwd": 90,  "lr": 108, "bond_pct":  5.0},
    "충청남도":        {"rwd": 90,  "lr": 108, "bond_pct":  4.0},
    "전북특별자치도":  {"rwd": 100, "lr": 120, "bond_pct":  5.0},
    "전라남도":        {"rwd": 120, "lr": 144, "bond_pct":  4.0},
    "경상북도":        {"rwd": 130, "lr": 156, "bond_pct":  4.0},
    "경상남도":        {"rwd": 100, "lr": 120, "bond_pct":  4.0},
    "제주특별자치도":  {"rwd": 180, "lr": 216, "bond_pct":  5.0},
}

# ─────────────────────────────────────────────────────────────────
# 헬퍼 함수
# ─────────────────────────────────────────────────────────────────

def fmt_man(won: float, decimal: bool = True) -> str:
    if decimal:
        return f"{round(won / 10_000, 1):,.1f}만원"
    return f"{round(won / 10_000):,}만원"

def calc_monthly(principal: float, months: int, annual_rate: float):
    if principal <= 0 or months <= 0:
        return 0.0, 0.0
    if annual_rate == 0:
        return principal / months, 0.0
    r = annual_rate / 100 / 12
    monthly = principal * r * math.pow(1 + r, months) / (math.pow(1 + r, months) - 1)
    return monthly, monthly * months - principal

def calc_acquisition_tax(car_price: float) -> dict:
    car_value       = car_price / 1.1
    raw_tax         = car_value * 0.07
    ev_discount     = min(raw_tax, 1_400_000)
    acquisition_tax = max(0, raw_tax - ev_discount)
    edu_tax         = acquisition_tax * 0.2
    return {
        "car_value":        car_value,
        "raw_tax":          raw_tax,
        "ev_discount":      ev_discount,
        "acquisition_tax":  acquisition_tax,
        "edu_tax":          edu_tax,
        "total":            acquisition_tax + edu_tax,
    }

def calc_bond(car_price: float, bond_pct: float, instant_discount: float) -> dict:
    car_value    = car_price / 1.1
    bond_amount  = car_value * (bond_pct / 100)
    actual_cost  = bond_amount * (instant_discount / 100)
    return {"bond_amount": bond_amount, "actual_cost": actual_cost}


# ─────────────────────────────────────────────────────────────────
# slider_with_input: 슬라이더 + 숫자 입력 칸 동기화 위젯
# ─────────────────────────────────────────────────────────────────

def slider_with_input(
    label: str,
    min_val: float,
    max_val: float,
    default: float,
    step: float,
    key: str,
    unit: str = "",
    help: str = None,
) -> float:
    """
    슬라이더와 숫자 입력 칸을 나란히 배치.
    둘 중 하나를 변경하면 나머지가 자동으로 동기화됩니다.
    session_state key: '{key}_val'
    """
    state_key = f"{key}_val"
    if state_key not in st.session_state:
        st.session_state[state_key] = default

    # 슬라이더가 바뀌면 number_input 값 갱신
    def on_slider():
        st.session_state[state_key] = st.session_state[f"{key}_slider"]

    # number_input이 바뀌면 slider 값 갱신
    def on_number():
        raw = st.session_state[f"{key}_number"]
        clamped = max(min_val, min(max_val, raw))
        st.session_state[state_key] = clamped

    col_label, col_slider, col_num = st.columns([2, 5, 2])
    with col_label:
        label_text = f"**{label}**"
        if unit:
            label_text += f" ({unit})"
        st.markdown(
            f"<div style='padding-top:6px;font-size:13px'>{label} "
            f"<span style='color:gray'>{unit}</span></div>",
            unsafe_allow_html=True,
        )

    with col_slider:
        st.slider(
            label,
            min_value=float(min_val),
            max_value=float(max_val),
            value=float(st.session_state[state_key]),
            step=float(step),
            key=f"{key}_slider",
            on_change=on_slider,
            label_visibility="collapsed",
            help=help,
        )

    with col_num:
        st.number_input(
            label,
            min_value=float(min_val),
            max_value=float(max_val),
            value=float(st.session_state[state_key]),
            step=float(step),
            key=f"{key}_number",
            on_change=on_number,
            label_visibility="collapsed",
            format="%.1f" if step < 1 else "%.0f",
        )

    return float(st.session_state[state_key])


def reset_slider(key: str, value: float):
    """슬라이더+입력칸 값을 외부에서 강제 리셋"""
    st.session_state[f"{key}_val"] = value


# ─────────────────────────────────────────────────────────────────
# Session State 초기화
# ─────────────────────────────────────────────────────────────────

for k, v in [
    ("prev_trim",   "Model Y Premium RWD"),
    ("prev_region", "서울특별시"),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────

st.title("테슬라 Model Y 할부 구매 시뮬레이터")
st.caption("테슬라 공식가격 · longrange.gg 보조금 · 취득세/공채 포함 | 2026년 3월 기준")
st.markdown(
    "<span style='font-size:12px;color:gray'>"
    "슬라이더를 드래그하거나 오른쪽 숫자 칸에 직접 입력하세요.</span>",
    unsafe_allow_html=True,
)

col_left, col_right = st.columns([1, 1], gap="large")

# ══════════════════════════════════════════════════════
# 왼쪽: 입력
# ══════════════════════════════════════════════════════
with col_left:

    # ── 트림 ──────────────────────────────────────────
    st.subheader("트림 선택")
    trim_name = st.radio(
        "트림",
        list(TRIMS.keys()),
        label_visibility="collapsed",
        format_func=lambda x: (
            f"{x}  —  {TRIMS[x]['price']//10_000:,}만원  |  {TRIMS[x]['spec']}"
        ),
    )
    trim_key   = TRIMS[trim_name]["key"]
    base_price = TRIMS[trim_name]["price"]

    use_custom = st.toggle("출고가 직접 입력", value=False)
    if use_custom:
        custom_man = st.number_input(
            "출고가 (만원)",
            min_value=0, max_value=50_000,
            value=base_price // 10_000, step=10,
        )
        base_price = custom_man * 10_000

    # ── 옵션 ──────────────────────────────────────────
    st.subheader("옵션")
    opt_total = 0
    for opt_name, opt_choices in OPTIONS.items():
        chosen     = st.selectbox(opt_name, list(opt_choices.keys()))
        opt_total += opt_choices[chosen]

    car_price = base_price + opt_total

    if car_price >= 57_000_000:
        st.warning(
            f"출고가 {fmt_man(car_price)}은 5,700만원을 초과합니다. "
            "Long Range AWD는 보조금 미지급 가능성이 있습니다."
        )
    st.info(
        f"옵션 합계: **+{fmt_man(opt_total)}**  |  출고가 합계: **{fmt_man(car_price)}**"
    )

    # ── 보조금 ────────────────────────────────────────
    st.subheader("보조금")
    st.caption("longrange.gg · 2026-03-14 / 환경부 무공해차 통합누리집")

    with st.expander("광역시도별 보조금 참고표 (개인 구매 기준)"):
        sub_rows = []
        for rname, rdata in REGIONS.items():
            g_rwd = TRIMS["Model Y Premium RWD"]["gov"]
            g_lr  = TRIMS["Model Y Premium Long Range AWD"]["gov"]
            sub_rows.append({
                "지역":           rname,
                "RWD 지방(만)":   rdata["rwd"],
                "RWD 합계(만)":   g_rwd + rdata["rwd"],
                "LR 지방(만)":    rdata["lr"],
                "LR 합계(만)":    g_lr  + rdata["lr"],
            })
        st.dataframe(pd.DataFrame(sub_rows).set_index("지역"), use_container_width=True)
        st.caption(
            "* 시군구 단위로 금액이 크게 다릅니다. "
            "정확한 금액은 ev.or.kr 또는 거주 지자체에서 확인하세요."
        )

    region = st.selectbox("지역 (광역시도)", list(REGIONS.keys()))

    # 트림/지역 변경 시 슬라이더 자동 리셋
    if trim_name != st.session_state.prev_trim or region != st.session_state.prev_region:
        reset_slider("gov",   TRIMS[trim_name]["gov"])
        reset_slider("local", REGIONS[region][trim_key])
        st.session_state.prev_trim   = trim_name
        st.session_state.prev_region = region
        st.rerun()

    gov_sub   = slider_with_input("국가 보조금", 0, 500, TRIMS[trim_name]["gov"], 5,  "gov",   "만원")
    local_sub = slider_with_input("지방 보조금", 0, 300, REGIONS[region][trim_key], 1, "local", "만원")

    use_convert   = st.checkbox("내연기관 전환지원금 포함 (2026년 신설, 조건 충족 시)", value=False)
    convert_bonus = 0
    if use_convert:
        convert_bonus = slider_with_input("전환지원금", 0, 100, 50, 5, "convert", "만원",
                                          help="지자체마다 다름. 직접 확인 후 입력하세요.")

    total_sub_won = (gov_sub + local_sub + convert_bonus) * 10_000
    net_price     = max(0, car_price - total_sub_won)
    st.success(
        f"실구매가: **{fmt_man(net_price)}** (보조금 총 {fmt_man(total_sub_won)} 차감)"
    )

    # ── 취등록비 ──────────────────────────────────────
    st.subheader("취등록비")
    st.caption(
        "전기차 취득세 최대 140만원 감면 (2026년 12월까지) · "
        "공채: 지역별 매입비율 × 즉시 할인 매도율"
    )

    bond_pct_default = REGIONS[region]["bond_pct"]
    bond_discount    = slider_with_input(
        f"공채 즉시 할인 매도율 ({region} 매입비율 {bond_pct_default:.0f}%)",
        5, 15, 10, 1, "bond_discount", "%",
        help="공채를 즉시 은행에 되팔 때 할인율. 금리에 따라 보통 8~12%.",
    )

    tax_data  = calc_acquisition_tax(car_price)
    bond_data = calc_bond(car_price, bond_pct_default, bond_discount)
    misc_reg  = 100_000
    total_reg = tax_data["total"] + bond_data["actual_cost"] + misc_reg

    rc1, rc2 = st.columns(2)
    rc1.metric("취득세 (감면 후)", fmt_man(tax_data["acquisition_tax"]))
    rc1.metric("지방교육세",       fmt_man(tax_data["edu_tax"]))
    rc2.metric(f"공채 실부담 ({bond_pct_default:.0f}%×{bond_discount:.0f}% 할인)",
               fmt_man(bond_data["actual_cost"]))
    rc2.metric("번호판·인지대 등", fmt_man(misc_reg))
    st.info(f"취등록비 합계: **{fmt_man(total_reg)}**")

    # ── 할부 조건 ─────────────────────────────────────
    st.subheader("할부 조건")
    st.caption("삼성카드 다이렉트 오토 기준")

    # 선수금 session_state 초기화 (실구매가 기반 기본값 20%)
    default_down_man = round(net_price * 0.20 / 10_000)
    if "down_won_man" not in st.session_state:
        st.session_state["down_won_man"] = default_down_man

    # ① 선수금 액수 입력
    max_down_man = max(1, round(net_price / 10_000))
    d1, d2, d3 = st.columns([3, 3, 2])
    with d1:
        st.markdown(
            "<div style='padding-top:6px;font-size:13px'>"
            "<b>선수금 액수</b> <span style='color:gray'>만원</span></div>",
            unsafe_allow_html=True,
        )
    with d2:
        down_man = st.number_input(
            "선수금 액수",
            min_value=0,
            max_value=max_down_man,
            value=min(int(st.session_state["down_won_man"]), max_down_man),
            step=10,
            key="down_won_man",
            label_visibility="collapsed",
            help="만원 단위로 입력하세요. 실구매가 기준 비율이 아래에 자동 표시됩니다.",
        )
    with d3:
        st.markdown(
            f"<div style='padding-top:8px;font-size:13px;color:gray'>"
            f"최대 {max_down_man:,}만원</div>",
            unsafe_allow_html=True,
        )

    # ② 선수금 비율 — 읽기 전용 자동 계산
    down_amt = down_man * 10_000
    down_pct = (down_amt / net_price * 100) if net_price > 0 else 0.0
    principal = max(0, net_price - down_amt)

    r1, r2, r3 = st.columns([3, 3, 2])
    with r1:
        st.markdown(
            "<div style='padding-top:6px;font-size:13px'>"
            "선수금 비율 <span style='color:gray'>(자동)</span></div>",
            unsafe_allow_html=True,
        )
    with r2:
        st.markdown(
            f"<div style='padding:6px 12px;background:var(--secondary-background-color);"
            f"border-radius:6px;font-size:15px;font-weight:600;color:#1D9E75'>"
            f"{down_pct:.1f}%</div>",
            unsafe_allow_html=True,
        )
    with r3:
        st.markdown(
            f"<div style='padding-top:8px;font-size:13px;color:gray'>"
            f"할부원금 {fmt_man(principal)}</div>",
            unsafe_allow_html=True,
        )

    annual_rate = slider_with_input("연 할부금리",  0, 12,  2.3, 0.1, "rate",  "%")

    months_options = [24, 36, 48, 60]
    months = st.select_slider("할부 기간", options=months_options, value=60)

    # ── 월 유지비 ─────────────────────────────────────
    st.subheader("월 유지비")
    ins_man    = slider_with_input("보험료",     5,  30, 12, 1, "ins",    "만원/월")
    charge_man = slider_with_input("충전비",     2,  15,  7, 1, "charge", "만원/월")
    misc_man   = slider_with_input("기타 유지비", 0, 10,  2, 1, "misc",   "만원/월")

    ins    = ins_man    * 10_000
    charge = charge_man * 10_000
    misc   = misc_man   * 10_000


# ══════════════════════════════════════════════════════
# 오른쪽: 결과
# ══════════════════════════════════════════════════════
with col_right:
    st.subheader("결과 요약")

    monthly_loan, total_interest = calc_monthly(principal, months, annual_rate)
    monthly_principal = principal / months if months > 0 else 0
    monthly_interest  = monthly_loan - monthly_principal
    monthly_maint     = ins + charge + misc
    grand_total       = monthly_loan + monthly_maint

    # 초기 지출
    st.markdown("#### 초기 지출 (출고 시)")
    ic1, ic2, ic3 = st.columns(3)
    ic1.metric("출고가",      fmt_man(car_price))
    ic2.metric("보조금 차감", f"-{fmt_man(total_sub_won)}")
    ic3.metric("실구매가",    fmt_man(net_price))

    ic4, ic5, ic6 = st.columns(3)
    ic4.metric("선수금",           fmt_man(down_amt),    f"{down_pct:.0f}%")
    ic5.metric("취등록비",         fmt_man(total_reg),   "전기차 감면 적용")
    ic6.metric("출고 당일 총지출", fmt_man(down_amt + total_reg))

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
        a.markdown(
            f"<span style='color:gray;font-size:14px'>{label}</span>",
            unsafe_allow_html=True,
        )
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
            "기간":      f"{m}개월",
            "월 할부금": fmt_man(ml),
            "월 총비용": fmt_man(ml + monthly_maint),
            "총 이자":   fmt_man(ti) if ti > 0 else "없음",
        })
    st.table(rows)

    # 5년 총 보유 비용
    st.markdown("#### 5년 총 보유 비용")
    total_60 = grand_total * 60 + down_amt + total_reg
    st.info(
        f"출고 당일: {fmt_man(down_amt + total_reg)}  \n"
        f"월 {fmt_man(grand_total)} × 60개월  \n\n"
        f"**5년 합계: {fmt_man(total_60)}** (유지비·취등록비 포함)"
    )

    # 취등록비 상세
    with st.expander("취등록비 계산 상세 보기"):
        st.markdown(
            f"""
| 항목 | 금액 | 비고 |
|------|------|------|
| 차량가액 (부가세 제외) | {fmt_man(tax_data['car_value'])} | 출고가 ÷ 1.1 |
| 취득세 (7%) | {fmt_man(tax_data['raw_tax'])} | 차량가액 × 7% |
| 전기차 감면 | -{fmt_man(tax_data['ev_discount'])} | 최대 140만원 (2026.12월까지) |
| **실 취득세** | **{fmt_man(tax_data['acquisition_tax'])}** | |
| 지방교육세 | {fmt_man(tax_data['edu_tax'])} | 취득세 × 20% |
| 공채매입액 | {fmt_man(bond_data['bond_amount'])} | 차량가액 × {bond_pct_default:.0f}% |
| 공채 즉시 매도 실부담 | {fmt_man(bond_data['actual_cost'])} | 할인율 {bond_discount:.0f}% 적용 |
| 번호판·인지대 등 | {fmt_man(misc_reg)} | 추정값 |
| **취등록비 합계** | **{fmt_man(total_reg)}** | |
"""
        )
        st.caption(
            "취득세: 지방세특례제한법 제66조 | "
            "공채매입비율: 지역별 조례 | "
            "실제 납부액은 등록 시 확인하세요."
        )

    st.caption("본 시뮬레이터는 참고용입니다. 실제 조건은 테슬라·삼성카드·지자체에서 확인하세요.")