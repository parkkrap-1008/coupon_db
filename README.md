# coupon_db

[connections.gsheets]
type = "sheets"
spreadsheet = "https://docs.google.com/spreadsheets/d/https://docs.google.com/spreadsheets/d/10P_7MrRgFSH9s4ro00e_OKoePn8-aD-_5pIrhDydsTE/edit?usp=sharing/edit"
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. 페이지 기본 설정 및 보안 (비밀번호 확인)
st.set_page_config(page_title="나만의 쿠폰 관리 앱", page_icon="🎫", layout="centered")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.subheader("🔒 인증이 필요한 페이지입니다.")
    password = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("로그인"):
        if password == "0510":
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop() # 비밀번호 통과 못 하면 아래 코드 실행 안 됨

# 2. 구글 스프레드시트 연결 초기화
conn = st.connection("gsheets", type=GSheetsConnection)

# 구글 시트에서 데이터 읽어오는 함수
def load_data():
    try:
        return conn.read(ttl="0d") # 캐시 없이 실시간으로 가져옴
    except:
        # 시트가 비어있을 경우를 대비한 기본 데이터프레임
        return pd.DataFrame(columns=["쿠폰명", "혜택", "상태", "생성일"])

df = load_data()

# 3. 페이지 네비게이션 설정 (기본값은 '쿠폰 보기' 메인 페이지)
if "page" not in st.session_state:
    st.session_state.page = "main"

# --- [메인 페이지: 쿠폰 사용 및 확인] ---
if st.session_state.page == "main":
    st.title("🎫 나의 쿠폰 지갑")
    st.write("현재 보유 중인 쿠폰 목록입니다. 사용 상태를 변경할 수 있습니다.")
    st.divider()

    if df.empty:
        st.info("등록된 쿠폰이 없습니다. 아래 수정 페이지에서 쿠폰을 추가해보세요!")
    else:
        # 쿠폰들을 카드 형태로 출력
        for index, row in df.iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.subheader(row["쿠폰명"])
                    st.caption(f"생성일: {row['생성일']}")
                with col2:
                    st.write(f"🎁 **혜택:** {row['혜택']}")
                    # 상태에 따라 색상 다르게 표시
                    if row["상태"] == "미사용":
                        st.success("🟢 미사용")
                    else:
                        st.error("🔴 사용완료")
                with col3:
                    # 상태 변경 버튼
                    if row["상태"] == "미사용":
                        if st.button("사용하기", key=f"use_{index}"):
                            df.at[index, "상태"] = "사용완료"
                            conn.update(data=df)
                            st.toast(f"'{row['쿠폰명']}' 쿠폰을 사용 처리했습니다!")
                            st.rerun()
                    else:
                        if st.button("되돌리기", key=f"unuse_{index}"):
                            df.at[index, "상태"] = "미사용"
                            conn.update(data=df)
                            st.toast(f"'{row['쿠폰명']}' 쿠폰을 미사용 처리했습니다.")
                            st.rerun()

    # 맨 아래 작게 관리자/수정 페이지 이동 버튼 생성
    st.write("")
    st.write("")
    st.divider()
    col_left, col_right = st.columns([4, 1])
    with col_right:
        if st.button("⚙️ 쿠폰 관리/수정", size="small"):
            st.session_state.page = "management"
            st.rerun()

# --- [서브 페이지: 쿠폰 수정 및 추가] ---
elif st.session_state.page == "management":
    st.title("⚙️ 쿠폰 관리 및 추가 페이지")
    st.write("새로운 쿠폰을 발급하거나 기존 쿠폰을 삭제할 수 있습니다.")
    
    if st.button("⬅️ 메인 화면(쿠폰 지갑)으로 돌아가기"):
        st.session_state.page = "main"
        st.rerun()
        
    st.divider()

    # 1. 새 쿠폰 추가 양식
    st.subheader("➕ 새 쿠폰 만들기")
    with st.form("new_coupon_form", clear_on_submit=True):
        new_name = st.text_input("쿠폰 이름 (예: 생일 축하 쿠폰)")
        new_benefit = st.text_input("쿠폰 혜택 (예: 맛있는 저녁 사주기)")
        submitted = st.form_submit_button("쿠폰 발급하기")
        
        if submitted:
            if new_name and new_benefit:
                new_row = {
                    "쿠폰명": new_name,
                    "혜택": new_benefit,
                    "상태": "미사용",
                    "생성일": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                # 기존 데이터에 추가 후 구글 시트 업데이트
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                conn.update(data=df)
                st.success(f"'{new_name}' 쿠폰이 성공적으로 저장되었습니다!")
                st.rerun()
            else:
                st.warning("쿠폰 이름과 혜택을 모두 입력해주세요.")

    st.divider()

    # 2. 기존 쿠폰 삭제 기능
    st.subheader("🗑️ 쿠폰 삭제하기")
    if df.empty:
        st.text("삭제할 쿠폰이 없습니다.")
    else:
        # 삭제할 쿠폰 선택
        coupon_to_delete = st.selectbox("삭제할 쿠폰을 선택하세요", df["쿠폰명"].tolist())
        if st.button("선택한 쿠폰 영구 삭제", type="primary"):
            df = df[df["쿠폰명"] != coupon_to_delete]
            conn.update(data=df)
            st.success(f"'{coupon_to_delete}' 쿠폰이 삭제되었습니다.")
            st.rerun()
