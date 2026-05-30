import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. 페이지 기본 설정
st.set_page_config(page_title="우리의 쿠폰 지갑", page_icon="🎫", layout="centered")

# --- 세션 상태(임시 기억 장치) 초기화 ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "selected_user" not in st.session_state:
    st.session_state.selected_user = None # 선택된 사용자 (지현/세연)
if "page" not in st.session_state:
    st.session_state.page = "main"

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

# 3. 사용자 선택 화면 ('지현' or '세연')
if st.session_state.selected_user is None:
    st.title("👋 환영합니다! 누구의 지갑을 열어볼까요?")
    st.write("사용할 사람의 이름을 선택해주세요.")
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👧 지현", use_container_width=True):
            st.session_state.selected_user = "지현"
            st.rerun()
    with col2:
        if st.button("👦 세연", use_container_width=True):
            st.session_state.selected_user = "세연"
            st.rerun()
    st.stop() # 사용자 선택 전까지는 아래 코드 실행 안 함

# --- 공통 데이터 불러오기 ---
current_user = st.session_state.selected_user
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(ttl="0d")
        # 데이터가 비어있거나 '소유자' 열이 없는 초기 상태를 위한 처리
        if df.empty or "소유자" not in df.columns:
            return pd.DataFrame(columns=["쿠폰명", "혜택", "상태", "생성일", "소유자"])
        # 빈 줄(NaN) 완벽 제거
        return df.dropna(how="all")
    except:
        return pd.DataFrame(columns=["쿠폰명", "혜택", "상태", "생성일", "소유자"])

df = load_data()

# 전체 데이터 중 '현재 접속한 사람'의 쿠폰만 걸러내기
user_df = df[df["소유자"] == current_user]
user_coupon_count = len(user_df)

# --- [메인 페이지: 쿠폰 지갑] ---
if st.session_state.page == "main":
    # 상단 메뉴바 (로그아웃 및 사용자 변경)
    col_a, col_b = st.columns([3, 1])
    with col_b:
        if st.button("🔄 다른 사람 지갑 보기", size="small"):
            st.session_state.selected_user = None
            st.rerun()

    st.title(f"🎫 {current_user}의 쿠폰 지갑")
    st.write(f"현재 발급된 쿠폰: **{user_coupon_count} / 10 개**")
    st.divider()

    if user_df.empty:
        st.info("등록된 쿠폰이 없습니다. 아래 버튼을 눌러 새 쿠폰을 만들어보세요!")
    else:
        # 내 쿠폰들만 반복해서 출력
        for index, row in user_df.iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.subheader(row["쿠폰명"])
                    st.caption(f"생성일: {row['생성일']}")
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

    # 하단 수정 페이지 이동
    st.write("")
    st.divider()
    col_left, col_right = st.columns([4, 1])
    with col_right:
        if st.button("⚙️ 쿠폰 발급/삭제", size="small"):
            st.session_state.page = "management"
            st.rerun()

# --- [서브 페이지: 쿠폰 추가 및 삭제] ---
elif st.session_state.page == "management":
    st.title(f"⚙️ {current_user} 쿠폰 관리소")
    if st.button("⬅️ 내 지갑으로 돌아가기"):
        st.session_state.page = "main"
        st.rerun()
        
    st.divider()

    # 1. 새 쿠폰 추가 양식 (10개 제한)
    st.subheader("➕ 새 쿠폰 발급하기")
    if user_coupon_count >= 10:
        st.error(f"🚨 {current_user}님의 쿠폰이 이미 10개 꽉 찼습니다! 기존 쿠폰을 삭제해야 새로 발급할 수 있습니다.")
    else:
        with st.form("new_coupon_form", clear_on_submit=True):
            new_name = st.text_input("쿠폰 이름")
            new_benefit = st.text_input("쿠폰 혜택")
            submitted = st.form_submit_button("쿠폰 발급하기")
            
            if submitted:
                if new_name and new_benefit:
                    new_row = {
                        "쿠폰명": new_name,
                        "혜택": new_benefit,
                        "상태": "미사용",
                        "생성일": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "소유자": current_user  # 누가 가진 쿠폰인지 저장
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    conn.update(data=df)
                    st.success("쿠폰이 성공적으로 발급되었습니다!")
                    st.rerun()
                else:
                    st.warning("이름과 혜택을 모두 적어주세요.")

    st.divider()

    # 2. 쿠폰 삭제 기능
    st.subheader("🗑️ 기존 쿠폰 삭제하기")
    if user_df.empty:
        st.text("삭제할 쿠폰이 없습니다.")
    else:
        coupon_to_delete = st.selectbox("삭제할 쿠폰을 선택하세요", user_df["쿠폰명"].tolist())
        if st.button("영구 삭제", type="primary"):
            # 내가 가진 쿠폰 중 이름이 일치하는 것만 삭제 (다른 사람의 동일한 이름 쿠폰 보호)
            index_to_drop = user_df[user_df["쿠폰명"] == coupon_to_delete].index
            df = df.drop(index_to_drop)
            conn.update(data=df)
            st.success("삭제 완료!")
            st.rerun()
