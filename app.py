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
    st.session_state.page = "selection" 
if "selected_user" not in st.session_state:
    st.session_state.selected_user = None

# ==========================================
# [화면 0] 로그인 화면 (꾸미기 적용)
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #ff4b4b;'>💖 지현 & 세연 쿠폰 보관함 💖</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>두 사람만의 소중한 약속과 추억을 보관하는 곳입니다.</p>", unsafe_allow_html=True)
    st.write("")
    
    with st.container(border=True):
        st.subheader("🔒 입장하기")
        password = st.text_input("비밀번호를 입력해주세요", type="password")
        if st.button("문 열기", use_container_width=True):
            if password == "0510":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다. 다시 생각해보세요!")
    st.stop()

# --- 구글 시트 데이터 불러오기 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(ttl="0d")
        if df.empty or "소유자" not in df.columns:
            return pd.DataFrame(columns=["쿠폰명", "혜택", "상태", "생성일", "소유자", "만료일"])
        return df.dropna(how="all")
    except:
        return pd.DataFrame(columns=["쿠폰명", "혜택", "상태", "생성일", "소유자", "만료일"])

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
            
    st.write("")
    st.write("")
    st.divider()
    col_left, col_right = st.columns([4, 1])
    with col_right:
        if st.button("⚙️ 쿠폰 통합 관리"):
            st.session_state.page = "admin"
            st.rerun()


# ==========================================
# [화면 2] 개인 쿠폰 지갑 (조회 및 사용만 가능)
# ==========================================
elif st.session_state.page == "wallet":
    current_user = st.session_state.selected_user
    
    if st.button("⬅️ 사람 선택 화면으로 돌아가기"):
        st.session_state.page = "selection"
        st.session_state.selected_user = None
        st.rerun()
        
    user_df = df[df["소유자"] == current_user]
    # 미사용 쿠폰만 카운트
    active_count = len(user_df[user_df["상태"] == "미사용"])

    st.title(f"🎫 {current_user}의 쿠폰 지갑")
    st.write(f"현재 쓸 수 있는 쿠폰: **{active_count} / 10 개**")
    st.divider()

    if user_df.empty:
        st.info("현재 지갑이 텅 비어있습니다!")
    else:
        for index, row in user_df.iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                
                # 예전 데이터에 만료일이 없을 경우를 대비한 안전 장치
                exp_date = row.get("만료일", "제한 없음")
                if pd.isna(exp_date) or exp_date == "": 
                    exp_date = "제한 없음"

                with col1:
                    st.subheader(row["쿠폰명"])
                    st.caption(f"발급일: {row['생성일']} | **만료일: {exp_date}**")
                with col2:
                    st.write(f"🎁 **혜택:** {row['혜택']}")
                    if row["상태"] == "미사용":
                        st.success("🟢 미사용")
                    else:
                        st.secondary_button("🔴 사용완료", disabled=True, key=f"btn_{index}") # 회색 버튼처럼 보이게
                with col3:
                    if row["상태"] == "미사용":
                        if st.button("사용하기", key=f"use_{index}", type="primary"):
                            df.at[index, "상태"] = "사용완료"
                            conn.update(data=df)
                            st.balloons() # 🎈 파티 효과 (풍선 애니메이션)
                            st.rerun()
                    else:
                        if st.button("되돌리기", key=f"unuse_{index}"):
                            df.at[index, "상태"] = "미사용"
                            conn.update(data=df)
                            st.rerun()


# ==========================================
# [화면 3] 통합 쿠폰 관리소 (새 쿠폰, 빠른 발급, 내역 조회)
# ==========================================
elif st.session_state.page == "admin":
    if st.button("⬅️ 사람 선택 화면으로 돌아가기"):
        st.session_state.page = "selection"
        st.rerun()

    st.title("⚙️ 전체 쿠폰 관리소")
    st.write("발급부터 내역 확인까지 모두 관리할 수 있습니다.")
    st.divider()

    target_user = st.radio("누구의 쿠폰을 조작하시겠습니까?", ["지현", "세연"], horizontal=True)
    target_df = df[df["소유자"] == target_user]
    active_count = len(target_df[target_df["상태"] == "미사용"])

    # 💡 탭(Tab) 기능으로 메뉴 깔끔하게 분리
    tab1, tab2, tab3 = st.tabs(["➕ 상세 발급", "⚡ 빠른 발급", "📜 사용 내역 & 삭제"])

    # --- 탭 1: 상세 설정 발급 ---
    with tab1:
        st.subheader(f"{target_user}님 상세 쿠폰 만들기 (현재 남은 칸: {10 - active_count}개)")
        if active_count >= 10:
            st.error("🚨 사용 가능한 쿠폰이 10개가 넘어 더 발급할 수 없습니다!")
        else:
            with st.form(f"new_coupon_form", clear_on_submit=True):
                new_name = st.text_input("쿠폰 이름")
                new_benefit = st.text_input("쿠폰 혜택")
                
                expire_option = st.radio("유효기간 설정", ["3개월", "6개월", "1년", "직접 설정"], horizontal=True)
                custom_date = st.date_input("직접 설정 (위에서 '직접 설정' 선택 시 적용)")
                
                submitted = st.form_submit_button("발급하기")
                
                if submitted:
                    if new_name and new_benefit:
                        # 유효기간 날짜 계산
                        now = datetime.now()
                        if expire_option == "3개월":
                            expire_date = now + pd.DateOffset(months=3)
                        elif expire_option == "6개월":
                            expire_date = now + pd.DateOffset(months=6)
                        elif expire_option == "1년":
                            expire_date = now + pd.DateOffset(years=1)
                        else:
                            expire_date = pd.to_datetime(custom_date)
                            
                        expire_str = expire_date.strftime("%Y-%m-%d")

                        new_row = {
                            "쿠폰명": new_name,
                            "혜택": new_benefit,
                            "상태": "미사용",
                            "생성일": now.strftime("%Y-%m-%d"),
                            "소유자": target_user,
                            "만료일": expire_str
                        }
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        conn.update(data=df)
                        st.success(f"'{new_name}' 쿠폰 발급 완료! (만료일: {expire_str})")
                        st.rerun()
                    else:
                        st.warning("이름과 혜택을 모두 적어주세요.")

    # --- 탭 2: 빠른 발급 (원클릭) ---
    with tab2:
        st.subheader("버튼 한 번으로 자주 쓰는 쿠폰 발급")
        st.caption("기본 유효기간 3개월로 즉시 발급됩니다.")
        
        # 💡 오타 수정 완료된 빠른 발급 프리셋!
        presets = [
            {"이름": "💆 안마 30분", "혜택": "원할 때 언제든 시원한 안마 30분"},
            {"이름": "🍽️ 맛있는 밥 쏘기", "혜택": "먹고 싶은 메뉴로 맛있는 한 끼 사주기"},
            {"이름": "☕ 커피 배달", "혜택": "원하는 커피 사다 바치기"},
            {"이름": "🎬 영화 예매권", "혜택": "같이 보고 싶은 영화 쿨하게 예매해주기"}
        ]
        
        for p in presets:
            if st.button(f"➕ {p['이름']} 발급하기", use_container_width=True):
                if active_count >= 10:
                    st.error("쿠폰함이 가득 찼습니다!")
                else:
                    expire_str = (datetime.now() + pd.DateOffset(months=3)).strftime("%Y-%m-%d")
                    new_row = {
                        "쿠폰명": p["이름"],
                        "혜택": p["혜택"],
                        "상태": "미사용",
                        "생성일": datetime.now().strftime("%Y-%m-%d"),
                        "소유자": target_user,
                        "만료일": expire_str
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    conn.update(data=df)
                    st.success(f"'{p['이름']}' 쿠폰이 빠른 발급되었습니다!")
                    st.rerun()

    # --- 탭 3: 사용 내역 및 삭제 ---
    with tab3:
        st.subheader("📜 사용 내역")
        used_df = target_df[target_df["상태"] == "사용완료"]
        if used_df.empty:
            st.info("아직 사용한 쿠폰이 없습니다.")
        else:
            # 사용 내역을 보기 쉬운 표 형태로 출력
            st.dataframe(used_df[["쿠폰명", "혜택", "생성일"]], use_container_width=True, hide_index=True)
            
        st.divider()
        st.subheader("🗑️ 기존 쿠폰 영구 삭제")
        if target_df.empty:
            st.text("삭제할 쿠폰이 없습니다.")
        else:
            coupon_to_delete = st.selectbox("삭제할 쿠폰을 선택하세요", target_df["쿠폰명"].tolist())
            if st.button("선택한 쿠폰 영구 삭제", type="primary"):
                index_to_drop = target_df[target_df["쿠폰명"] == coupon_to_delete].index
                df = df.drop(index_to_drop)
                conn.update(data=df)
                st.success("쿠폰이 영구 삭제되었습니다.")
                st.rerun()
