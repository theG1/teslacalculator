"""
테슬라 Model Y 할부 구매 시뮬레이터
- 테슬라 공식 가격 (2026년 3월)
- 보조금: teslacharger.co.kr / 무공해차 통합누리집 실데이터 (2026-03-16)
- 트림별(RWD / Long Range) × 시군구별 지방비 완전 개별 반영
- 취등록비 계산 포함
- 선수금 액수 ↔ 비율 양방향 연동
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
# 상수
# ─────────────────────────────────────────────────────────────────

TRIMS = {
    "Model Y Premium RWD": {
        "key": "rwd",
        "price": 49_990_000,
        "gov": 170,
        "spec": "후륜구동 · 주행가능 400km · 제로백 5.9초",
    },
    "Model Y Premium Long Range AWD": {
        "key": "lr",
        "price": 59_990_000,
        "gov": 210,
        "spec": "사륜구동 · 주행가능 505km · 제로백 4.8초",
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

# ── 지역별 보조금 실데이터 ─────────────────────────────────────────
# 출처: teslacharger.co.kr (무공해차 통합누리집) 2026-03-16
# rwd: Model Y Premium RWD 지방비(만원)
# lr:  Model Y Premium Long Range AWD 지방비(만원)
# bond_pct: 공채매입비율(%)
REGIONS = {
    # ── 광역시·특별시·세종 ─────────────────────────────────────────
    "서울특별시":         {"rwd": 51,  "lr": 63,  "bond_pct": 12.0},
    "부산광역시":         {"rwd": 51,  "lr": 63,  "bond_pct":  4.0},
    "대구광역시":         {"rwd": 51,  "lr": 63,  "bond_pct":  4.0},
    "인천광역시":         {"rwd": 51,  "lr": 63,  "bond_pct":  5.0},
    "광주광역시":         {"rwd": 51,  "lr": 63,  "bond_pct":  5.0},
    "대전광역시":         {"rwd": 51,  "lr": 63,  "bond_pct":  4.0},
    "울산광역시":         {"rwd": 51,  "lr": 63,  "bond_pct":  4.0},
    "세종특별자치시":     {"rwd": 51,  "lr": 63,  "bond_pct":  4.0},
    # ── 경기도 시군 (개별 데이터) ─────────────────────────────────
    "경기 수원시":        {"rwd": 70,  "lr": 87,  "bond_pct":  9.0},
    "경기 성남시":        {"rwd": 76,  "lr": 94,  "bond_pct":  9.0},
    "경기 의정부시":      {"rwd": 62,  "lr": 77,  "bond_pct":  9.0},
    "경기 안양시":        {"rwd": 72,  "lr": 89,  "bond_pct":  9.0},
    "경기 부천시":        {"rwd": 51,  "lr": 63,  "bond_pct":  9.0},
    "경기 광명시":        {"rwd": 119, "lr": 147, "bond_pct":  9.0},
    "경기 평택시":        {"rwd": 85,  "lr": 105, "bond_pct":  9.0},
    "경기 동두천시":      {"rwd": 95,  "lr": 117, "bond_pct":  9.0},
    "경기 안산시":        {"rwd": 68,  "lr": 84,  "bond_pct":  9.0},
    "경기 고양시":        {"rwd": 68,  "lr": 84,  "bond_pct":  9.0},
    "경기 과천시":        {"rwd": 85,  "lr": 105, "bond_pct":  9.0},
    "경기 구리시":        {"rwd": 85,  "lr": 105, "bond_pct":  9.0},
    "경기 남양주시":      {"rwd": 51,  "lr": 63,  "bond_pct":  9.0},
    "경기 오산시":        {"rwd": 79,  "lr": 98,  "bond_pct":  9.0},
    "경기 시흥시":        {"rwd": 68,  "lr": 84,  "bond_pct":  9.0},
    "경기 군포시":        {"rwd": 82,  "lr": 101, "bond_pct":  9.0},
    "경기 의왕시":        {"rwd": 85,  "lr": 105, "bond_pct":  9.0},
    "경기 하남시":        {"rwd": 51,  "lr": 63,  "bond_pct":  9.0},
    "경기 용인시":        {"rwd": 73,  "lr": 91,  "bond_pct":  9.0},
    "경기 파주시":        {"rwd": 85,  "lr": 105, "bond_pct":  9.0},
    "경기 이천시":        {"rwd": 85,  "lr": 105, "bond_pct":  9.0},
    "경기 안성시":        {"rwd": 102, "lr": 126, "bond_pct":  9.0},
    "경기 김포시":        {"rwd": 68,  "lr": 84,  "bond_pct":  9.0},
    "경기 화성시":        {"rwd": 56,  "lr": 70,  "bond_pct":  9.0},
    "경기 광주시":        {"rwd": 51,  "lr": 63,  "bond_pct":  9.0},
    "경기 양주시":        {"rwd": 70,  "lr": 87,  "bond_pct":  9.0},
    "경기 포천시":        {"rwd": 68,  "lr": 84,  "bond_pct":  9.0},
    "경기 여주시":        {"rwd": 117, "lr": 144, "bond_pct":  9.0},
    "경기 연천군":        {"rwd": 161, "lr": 199, "bond_pct":  9.0},
    "경기 가평군":        {"rwd": 113, "lr": 140, "bond_pct":  9.0},
    "경기 양평군":        {"rwd": 113, "lr": 140, "bond_pct":  9.0},
    # ── 도 단위 (대표값, 참고용) ──────────────────────────────────
    "강원특별자치도":     {"rwd": 85,  "lr": 105, "bond_pct":  4.0},
    "충청북도":           {"rwd": 90,  "lr": 108, "bond_pct":  5.0},
    "충청남도":           {"rwd": 90,  "lr": 108, "bond_pct":  4.0},
    "전북특별자치도":     {"rwd": 100, "lr": 120, "bond_pct":  5.0},
    "전라남도":           {"rwd": 120, "lr": 144, "bond_pct":  4.0},
    "경상북도":           {"rwd": 130, "lr": 156, "bond_pct":  4.0},
    "경상남도":           {"rwd": 100, "lr": 120, "bond_pct":  4.0},
    "제주특별자치도":     {"rwd": 180, "lr": 216, "bond_pct":  5.0},
}

# ─────────────────────────────────────────────────────────────────
# 헬퍼 함수
# ─────────────────────────────────────────────────────────────────

def fmt_man(won: float) -> str:
    return f"{round(won / 10_000, 1):,.1f}만원"

def calc_monthly(principal: float, months: int, annual_rate: float):
    if principal <= 0 or months <= 0:
        return 0.0, 0.0
    if annual_rate == 0:
        return principal / months, 0.0
    r = annual_rate / 100 / 12
    m = principal * r * math.pow(1+r, months) / (math.pow(1+r, months) - 1)
    return m, m * months - principal

def calc_acquisition_tax(car_price: float) -> dict:
    car_value       = car_price / 1.1
    raw_tax         = car_value * 0.07
    ev_discount     = min(raw_tax, 1_400_000)
    acquisition_tax = max(0, raw_tax - ev_discount)
    edu_tax         = acquisition_tax * 0.2
    return {
        "car_value": car_value, "raw_tax": raw_tax,
        "ev_discount": ev_discount, "acquisition_tax": acquisition_tax,
        "edu_tax": edu_tax, "total": acquisition_tax + edu_tax,
    }

def calc_bond(car_price: float, bond_pct: float, instant_discount: float) -> dict:
    car_value   = car_price / 1.1
    bond_amount = car_value * (bond_pct / 100)
    actual_cost = bond_amount * (instant_discount / 100)
    return {"bond_amount": bond_amount, "actual_cost": actual_cost}

# ─────────────────────────────────────────────────────────────────
# 슬라이더 + 숫자 입력 동기화 위젯
# ─────────────────────────────────────────────────────────────────

def slider_with_input(label, min_val, max_val, default, step, key, unit="", help=None):
    sk = f"{key}_val"
    if sk not in st.session_state:
        st.session_state[sk] = float(default)

    def on_sl(): st.session_state[sk] = st.session_state[f"{key}_sl"]
    def on_nb(): st.session_state[sk] = max(float(min_val), min(float(max_val), st.session_state[f"{key}_nb"]))

    c1, c2, c3 = st.columns([2, 5, 2])
    with c1:
        st.markdown(
            f"<div style='padding-top:6px;font-size:13px'>{label} "
            f"<span style='color:gray'>{unit}</span></div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.slider(label, float(min_val), float(max_val), float(st.session_state[sk]),
                  float(step), key=f"{key}_sl", on_change=on_sl,
                  label_visibility="collapsed", help=help)
    with c3:
        st.number_input(label, float(min_val), float(max_val), float(st.session_state[sk]),
                        float(step), key=f"{key}_nb", on_change=on_nb,
                        label_visibility="collapsed",
                        format="%.1f" if step < 1 else "%.0f")
    return float(st.session_state[sk])

def reset_slider(key, value):
    st.session_state[f"{key}_val"] = float(value)

# ─────────────────────────────────────────────────────────────────
# Session State 초기화
# ─────────────────────────────────────────────────────────────────

for k, v in [("prev_trim", "Model Y Premium RWD"), ("prev_region", "서울특별시")]:
    if k not in st.session_state:
        st.session_state[k] = v
for k, v in [("dp_man", 0), ("dp_pct", 20.0), ("dp_init", False)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────

st.title("테슬라 Model Y 할부 구매 시뮬레이터")
st.caption("테슬라 공식가격 · 무공해차 통합누리집 실데이터(2026-03-16) · 취득세/공채 포함")
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
        "트림", list(TRIMS.keys()), label_visibility="collapsed",
        format_func=lambda x: f"{x}  —  {TRIMS[x]['price']//10_000:,}만원  |  {TRIMS[x]['spec']}",
    )
    trim_key   = TRIMS[trim_name]["key"]   # "rwd" or "lr"
    base_price = TRIMS[trim_name]["price"]
    gov_default = TRIMS[trim_name]["gov"]

    use_custom = st.toggle("출고가 직접 입력", value=False)
    if use_custom:
        base_price = st.number_input("출고가 (만원)", 0, 50_000, base_price // 10_000, 10) * 10_000

    # ── 옵션 ──────────────────────────────────────────
    st.subheader("옵션")
    opt_total = 0
    for opt_name, opt_choices in OPTIONS.items():
        chosen     = st.selectbox(opt_name, list(opt_choices.keys()))
        opt_total += opt_choices[chosen]

    car_price = base_price + opt_total

    # 2026년 가격 기준 안내
    if car_price >= 85_000_000:
        st.error(f"출고가 {fmt_man(car_price)} — 8,500만원 초과 · 국고 보조금 **미지급**")
    elif car_price >= 53_000_000:
        st.warning(
            f"출고가 {fmt_man(car_price)} — 5,300만~8,500만원 구간 · "
            f"국고 보조금 **50% 지급** (공시 금액에 반영됨)"
        )
    else:
        st.success(f"출고가 {fmt_man(car_price)} — 5,300만원 미만 · 국고 보조금 **100% 지급**")

    st.info(f"옵션 합계: **+{fmt_man(opt_total)}**  |  출고가 합계: **{fmt_man(car_price)}**")

    # ── 보조금 ────────────────────────────────────────
    st.subheader("보조금")
    st.caption("출처: 무공해차 통합누리집 (ev.or.kr) · 2026-03-16 기준")

    with st.expander("지역별 Model Y 보조금 전체 표"):
        rows = []
        for rname, rd in REGIONS.items():
            rows.append({
                "지역":           rname,
                "RWD 지방비(만)": rd["rwd"],
                "RWD 합계(만)":   TRIMS["Model Y Premium RWD"]["gov"] + rd["rwd"],
                "LR 지방비(만)":  rd["lr"],
                "LR 합계(만)":    TRIMS["Model Y Premium Long Range AWD"]["gov"] + rd["lr"],
            })
        df = pd.DataFrame(rows).set_index("지역")
        st.dataframe(df, use_container_width=True)
        st.caption(
            "단위: 만원 | 국비: RWD 170만 / Long Range 210만 | "
            "출처: teslacharger.co.kr / 무공해차 통합누리집 2026-03-16"
        )

    region = st.selectbox("지역", list(REGIONS.keys()))

    # 트림+지역에서 자동 계산 (session_state 미사용 → 항상 정확)
    gov_auto   = TRIMS[trim_name]["gov"]          # 국비: 트림에서
    local_auto = REGIONS[region][trim_key]         # 지방비: 트림키+지역에서

    # 보조금 자동 적용 카드
    sub_c1, sub_c2, sub_c3 = st.columns(3)
    sub_c1.metric("국가 보조금 (자동)", f"{gov_auto}만원",
                  f"{trim_name.split()[-1]} 트림 기준")
    sub_c2.metric("지방 보조금 (자동)", f"{local_auto}만원",
                  f"{region} 기준")
    sub_c3.metric("보조금 합계", f"{gov_auto + local_auto}만원",
                  "국비 + 지방비")

    # 수동 조정 (선택적)
    manual_override = st.checkbox("보조금 직접 수정 (공시 금액과 다른 경우)", value=False)
    if manual_override:
        st.caption("슬라이더 또는 오른쪽 숫자 칸으로 직접 입력하세요.")
        gov_sub   = slider_with_input("국가 보조금 (수정)", 0, 500, float(gov_auto),   5, "gov_ov",   "만원")
        local_sub = slider_with_input("지방 보조금 (수정)", 0, 400, float(local_auto), 1, "local_ov", "만원")
    else:
        # 수동 override session_state 항상 최신 자동값으로 동기화
        st.session_state["gov_ov_val"]   = float(gov_auto)
        st.session_state["local_ov_val"] = float(local_auto)
        gov_sub   = float(gov_auto)
        local_sub = float(local_auto)

    use_convert   = st.checkbox("내연기관 전환지원금 포함 (2026년 신설)", value=False)
    convert_bonus = 0
    if use_convert:
        convert_bonus = slider_with_input("전환지원금", 0, 100, 50, 5, "convert", "만원",
                                          help="3년 이상 보유 내연차 폐차·매각 후 전기차 구매 시. 지자체마다 다름.")

    total_sub_won = (gov_sub + local_sub + convert_bonus) * 10_000
    net_price     = max(0, car_price - total_sub_won)
    st.success(f"실구매가: **{fmt_man(net_price)}** (보조금 총 {fmt_man(total_sub_won)} 차감)")

    # ── 취등록비 ──────────────────────────────────────
    st.subheader("취등록비")
    st.caption("전기차 취득세 최대 140만원 감면 (2026.12월까지) · 공채 지역별 매입비율 적용")

    bond_pct_default = REGIONS[region]["bond_pct"]
    bond_discount = slider_with_input(
        f"공채 즉시 할인율 (매입비율 {bond_pct_default:.0f}%)",
        5, 15, 10, 1, "bond_discount", "%",
        help="공채를 즉시 은행에 되팔 때 할인율. 보통 8~12%."
    )
    tax_data  = calc_acquisition_tax(car_price)
    bond_data = calc_bond(car_price, bond_pct_default, bond_discount)
    misc_reg  = 100_000
    total_reg = tax_data["total"] + bond_data["actual_cost"] + misc_reg

    rc1, rc2 = st.columns(2)
    rc1.metric("취득세 (감면 후)", fmt_man(tax_data["acquisition_tax"]))
    rc1.metric("지방교육세",       fmt_man(tax_data["edu_tax"]))
    rc2.metric(f"공채 실부담 ({bond_pct_default:.0f}%×{bond_discount:.0f}%할인)",
               fmt_man(bond_data["actual_cost"]))
    rc2.metric("번호판·인지대 등", fmt_man(misc_reg))
    st.info(f"취등록비 합계: **{fmt_man(total_reg)}**")

    # ── 할부 조건 ─────────────────────────────────────
    st.subheader("할부 조건")
    st.caption("삼성카드 다이렉트 오토 기준")

    max_down_man = max(1, round(net_price / 10_000))
    if not st.session_state["dp_init"]:
        st.session_state["dp_man"] = round(net_price * 0.20 / 10_000)
        st.session_state["dp_pct"] = 20.0
        st.session_state["dp_init"] = True

    def _on_man():
        v = max(0, min(st.session_state["_dp_man"], max_down_man))
        st.session_state["dp_man"] = v
        st.session_state["dp_pct"] = round(v / max_down_man * 100, 1) if max_down_man else 0.0
    def _on_pct():
        p = max(0.0, min(100.0, st.session_state["_dp_pct"]))
        st.session_state["dp_pct"] = p
        st.session_state["dp_man"] = round(max_down_man * p / 100)

    a1, a2, a3 = st.columns([3, 3, 2])
    with a1:
        st.markdown("<div style='padding-top:6px;font-size:13px'><b>선수금 액수</b> <span style='color:gray'>만원</span></div>", unsafe_allow_html=True)
    with a2:
        st.number_input("선수금 액수", 0, max_down_man, int(st.session_state["dp_man"]), 10,
                        key="_dp_man", on_change=_on_man, label_visibility="collapsed")
    with a3:
        st.markdown(f"<div style='padding-top:8px;font-size:12px;color:gray'>최대 {max_down_man:,}만원</div>", unsafe_allow_html=True)

    b1, b2, b3 = st.columns([3, 3, 2])
    with b1:
        st.markdown("<div style='padding-top:6px;font-size:13px'><b>선수금 비율</b> <span style='color:gray'>%</span></div>", unsafe_allow_html=True)
    with b2:
        st.number_input("선수금 비율", 0.0, 100.0, float(st.session_state["dp_pct"]), 0.1,
                        format="%.1f", key="_dp_pct", on_change=_on_pct, label_visibility="collapsed")
    with b3:
        down_amt_preview = int(st.session_state["dp_man"]) * 10_000
        st.markdown(f"<div style='padding-top:8px;font-size:12px;color:gray'>할부원금 {fmt_man(max(0, net_price - down_amt_preview))}</div>", unsafe_allow_html=True)

    down_amt  = int(st.session_state["dp_man"]) * 10_000
    down_pct  = float(st.session_state["dp_pct"])
    principal = max(0, net_price - down_amt)

    annual_rate = slider_with_input("연 할부금리", 0, 12, 2.3, 0.1, "rate", "%")
    months      = st.select_slider("할부 기간", options=[24, 36, 48, 60], value=60)

    # ── 월 유지비 ─────────────────────────────────────
    st.subheader("월 유지비")
    ins    = slider_with_input("보험료",      5,  30, 12, 1, "ins",    "만원/월") * 10_000
    charge = slider_with_input("충전비",      2,  15,  7, 1, "charge", "만원/월") * 10_000
    misc   = slider_with_input("기타 유지비", 0,  10,  2, 1, "misc",   "만원/월") * 10_000


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
    ic4.metric("선수금",           fmt_man(down_amt),           f"{down_pct:.1f}%")
    ic5.metric("취등록비",         fmt_man(total_reg),          "전기차 감면 적용")
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
    for lbl, val in details:
        a, b = st.columns([2, 1])
        a.markdown(f"<span style='color:gray;font-size:14px'>{lbl}</span>", unsafe_allow_html=True)
        b.markdown(f"**{val}**")

    st.divider()
    a, b = st.columns([2, 1])
    a.markdown("### 월 총 비용")
    b.markdown(f"### {fmt_man(grand_total)}")
    if total_interest > 0:
        st.caption(f"전체 기간 총 이자: {fmt_man(total_interest)}")
    else:
        st.caption("전체 기간 총 이자: 없음 (무이자)")

    st.divider()

    # 기간별 비교
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
    with st.expander("취등록비 계산 상세"):
        st.markdown(f"""
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
""")
        st.caption("취득세: 지방세특례제한법 제66조 | 공채매입비율: 지역별 조례 | 실제 납부액은 등록 시 확인하세요.")

    st.caption("본 시뮬레이터는 참고용입니다. 실제 조건은 테슬라·삼성카드·지자체에서 확인하세요.")