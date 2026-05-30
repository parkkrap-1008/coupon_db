import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. 페이지 기본 설정
st.set_page_config(page_title="우리의 쿠폰 앱", page_icon="🎫", layout="centered")

# --- 상태 관리 (초기화) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page" not in st.session_state:
    st.session_state.page = "selection" # selection(선택), wallet(지갑), admin(관리소)
if "selected_user" not in st.session_state:
    st.session_state.selected_user = None

# 2. 로그인 화면 (비밀번호 0510)
if not st.session_state.logged_in:
    st.subheader("🔒 인증이 필요한 페이지입니다.")
    password = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("로그인"):
        if password == "0510":
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop()

# --- 구글 시트 데이터 불러오기 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(ttl="0d")
        if df.empty or "소유자" not in df.columns:
            return pd.DataFrame(columns=["쿠폰명", "혜택", "상태", "생성일", "소유자"])
        return df.dropna(how="all")
    except:
        return pd.DataFrame(columns=["쿠폰명", "혜택", "상태", "생성일", "소유자"])

df = load_data()


# ==========================================
# [화면 1] 사용자 선택 첫 화면
# ==========================================
if st.session_state.page == "selection":
    st.title("👋 환영합니다!")
    st.write("누구의 쿠폰 지갑을 열어볼까요?")
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👧 지현 지갑 보기", use_container_width=True, type="primary"):
            st.session_state.selected_user = "지현"
            st.session_state.page = "wallet"
            st.rerun()
    with col2:
        if st.button("👦 세연 지갑 보기", use_container_width=True, type="primary"):
            st.session_state.selected_user = "세연"
            st.session_state.page = "wallet"
            st.rerun()
            
    # 맨 아래 작게 관리자 페이지 이동 버튼 생성
    st.write("")
    st.write("")
    st.divider()
    col_left, col_right = st.columns([4, 1])
    with col_right:
        if st.button("⚙️ 쿠폰 통합 관리", size="small"):
            st.session_state.page = "admin"
            st.rerun()


# ==========================================
# [화면 2] 개인 쿠폰 지갑 (조회 및 사용만 가능)
# ==========================================
elif st.session_state.page == "wallet":
    current_user = st.session_state.selected_user
    
    # 처음으로 돌아가는 버튼
    if st.button("⬅️ 사람 선택 화면으로 돌아가기"):
        st.session_state.page = "selection"
        st.session_state.selected_user = None
        st.rerun()
        
    user_df = df[df["소유자"] == current_user]
    user_coupon_count = len(user_df)

    st.title(f"🎫 {current_user}의 쿠폰 지갑")
    st.write(f"현재 보유 중인 쿠폰: **{user_coupon_count} / 10 개**")
    st.divider()

    if user_df.empty:
        st.info("현재 지갑이 텅 비어있습니다!")
    else:
        for index, row in user_df.iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.subheader(row["쿠폰명"])
                    st.caption(f"발급일: {row['생성일']}")
                with col2:
                    st.write(f"🎁 **혜택:** {row['혜택']}")
                    if row["상태"] == "미사용":
                        st.success("🟢 미사용")
                    else:
                        st.error("🔴 사용완료")
                with col3:
                    if row["상태"] == "미사용":
                        if st.button("사용하기", key=f"use_{index}"):
                            df.at[index, "상태"] = "사용완료"
                            conn.update(data=df)
                            st.rerun()
                    else:
                        if st.button("되돌리기", key=f"unuse_{index}"):
                            df.at[index, "상태"] = "미사용"
                            conn.update(data=df)
                            st.rerun()


# ==========================================
# [화면 3] 통합 쿠폰 관리소 (추가/삭제)
# ==========================================
elif st.session_state.page == "admin":
    # 처음으로 돌아가는 버튼
    if st.button("⬅️ 사람 선택 화면으로 돌아가기"):
        st.session_state.page = "selection"
        st.rerun()

    st.title("⚙️ 전체 쿠폰 관리소")
    st.write("이곳에서 두 사람의 쿠폰을 모두 발급하거나 삭제할 수 있습니다.")
    st.divider()

    # 누구의 쿠폰을 조작할지 선택
    target_user = st.radio("누구의 쿠폰을 수정하시겠습니까?", ["지현", "세연"], horizontal=True)
    
    # 선택된 사람의 데이터만 필터링
    target_df = df[df["소유자"] == target_user]
    current_count = len(target_df)

    # 1. 새 쿠폰 발급 영역
    st.subheader(f"➕ {target_user}님 새 쿠폰 발급 (현재 {current_count}/10개)")
    
    if current_count >= 10:
        st.error(f"🚨 {target_user}님의 쿠폰함이 가득 찼습니다! (최대 10개). 기존 쿠폰을 삭제해야 추가할 수 있습니다.")
    else:
        with st.form(f"new_coupon_{target_user}", clear_on_submit=True):
            new_name = st.text_input("쿠폰 이름 (예: 안마 30분)")
            new_benefit = st.text_input("쿠폰 혜택 (예: 원할 때 언제든 안마해주기)")
            submitted = st.form_submit_button(f"{target_user}에게 쿠폰 발급하기")
            
            if submitted:
                if new_name and new_benefit:
                    new_row = {
                        "쿠폰명": new_name,
                        "혜택": new_benefit,
                        "상태": "미사용",
                        "생성일": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "소유자": target_user
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    conn.update(data=df)
                    st.success(f"'{new_name}' 쿠폰이 발급되었습니다!")
                    st.rerun()
                else:
                    st.warning("쿠폰 이름과 혜택을 모두 적어주세요.")

    st.divider()

    # 2. 기존 쿠폰 삭제 영역
    st.subheader(f"🗑️ {target_user}님 쿠폰 삭제하기")
    if target_df.empty:
        st.text(f"{target_user}님은 삭제할 쿠폰이 없습니다.")
    else:
        coupon_to_delete = st.selectbox(f"삭제할 {target_user}님의 쿠폰 선택", target_df["쿠폰명"].tolist())
        if st.button(f"선택한 쿠폰 영구 삭제", type="primary"):
            # 소유자가 일치하면서 이름도 일치하는 쿠폰의 인덱스 찾아서 삭제
            index_to_drop = target_df[target_df["쿠폰명"] == coupon_to_delete].index
            df = df.drop(index_to_drop)
            conn.update(data=df)
            st.success(f"'{coupon_to_delete}' 쿠폰이 삭제되었습니다.")
            st.rerun()
