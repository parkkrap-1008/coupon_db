import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import hashlib

# 자동 로그인 마법 부품
try:
    from streamlit_cookies_controller import CookieController
    has_cookies = True
except ImportError:
    has_cookies = False

# 1. 페이지 기본 설정
st.set_page_config(page_title="우리의 쿠폰 앱", page_icon="🎫", layout="centered")

if has_cookies:
    controller = CookieController()
else:
    controller = None

# --- 상태 관리 (초기화) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "page" not in st.session_state:
    st.session_state.page = "selection" 
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"

# --- 🚀 자동 로그인 확인 로직 ---
if not st.session_state.logged_in and has_cookies:
    saved_user = controller.get("auto_login_user")
    if saved_user:
        st.session_state.logged_in = True
        st.session_state.current_user = saved_user
        st.session_state.page = "selection"
        st.rerun()

# --- 구글 시트 데이터 연결 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def update_data(worksheet_name, new_data):
    conn.update(worksheet=worksheet_name, data=new_data)
    st.cache_data.clear() 

def load_users():
    try:
        users = conn.read(worksheet="회원", ttl="10m") 
        if users.empty or "아이디" not in users.columns:
            return pd.DataFrame(columns=["이름", "아이디", "비밀번호", "스티커"])
        return users.dropna(how="all")
    except:
        return pd.DataFrame(columns=["이름", "아이디", "비밀번호", "스티커"])

def load_data():
    try:
        df = conn.read(worksheet="쿠폰", ttl="10m") 
        if df.empty or "소유자" not in df.columns:
            return pd.DataFrame(columns=["쿠폰명", "혜택", "상태", "생성일", "소유자", "만료일", "사용일", "메모"])
        return df.dropna(how="all")
    except:
        return pd.DataFrame(columns=["쿠폰명", "혜택", "상태", "생성일", "소유자", "만료일", "사용일", "메모"])

users_df = load_users()
df = load_data()

# 스티커 판 데이터 빈칸 방어 로직
if "스티커" not in users_df.columns:
    users_df["스티커"] = 0
users_df["스티커"] = pd.to_numeric(users_df["스티커"], errors='coerce').fillna(0).astype(int)

if "사용일" not in df.columns:
    df["사용일"] = ""
if "메모" not in df.columns:
    df["메모"] = ""

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ==========================================
# [화면 0] 로그인 & 회원가입 화면
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #4B4B4B;'>지현 & 세연 쿠폰 보관함</h1>", unsafe_allow_html=True)
    st.write("")
    
    if not has_cookies:
        st.warning("💡 자동 로그인 기능을 켜시려면 깃허브 requirements.txt에 `streamlit-cookies-controller`를 꼭 추가해주세요!")

    if st.session_state.auth_mode == "login":
        with st.container(border=True):
            st.subheader("로그인")
            login_id = st.text_input("아이디")
            login_pw = st.text_input("비밀번호", type="password")
            
            if st.button("로그인", use_container_width=True, type="primary"):
                if login_id and login_pw:
                    hashed_pw = hash_password(login_pw)
                    user_match = users_df[(users_df["아이디"] == login_id) & (users_df["비밀번호"] == hashed_pw)]
                    
                    if not user_match.empty:
                        matched_name = user_match.iloc[0]["이름"]
                        if has_cookies:
                            # 💡 모바일 브라우저가 지우지 못하도록 보안 옵션(secure, samesite)을 꽉꽉 채워 넣었습니다!
                            controller.set("auto_login_user", matched_name, max_age=31536000, path="/", secure=True, sameSite="None")
                            
                        st.session_state.logged_in = True
                        st.session_state.current_user = matched_name
                        st.session_state.page = "selection" 
                        st.rerun()
                    else:
                        st.error("아이디나 비밀번호가 틀렸습니다. 다시 확인해주세요!")
                else:
                    st.warning("아이디와 비밀번호를 모두 입력해주세요.")
        
        st.write("")
        if st.button("아직 계정이 없으신가요? 📝 회원가입 하기", use_container_width=True):
            st.session_state.auth_mode = "signup"
            st.rerun()

    else:
        with st.container(border=True):
            st.subheader("회원가입")
            st.caption("처음 오셨나요? 본인의 이름으로 가입을 진행해주세요.")
            signup_name = st.radio("나는 누구인가요?", ["지현", "세연"], horizontal=True)
            signup_id = st.text_input("사용할 새로운 아이디")
            signup_pw = st.text_input("사용할 비밀번호", type="password")
            signup_pw_check = st.text_input("비밀번호 한 번 더 입력", type="password")
            
            if st.button("가입하기", use_container_width=True, type="primary"):
                if signup_id and signup_pw and signup_pw_check:
                    if signup_pw != signup_pw_check:
                        st.error("입력하신 두 비밀번호가 서로 다릅니다!")
                    elif signup_id in users_df["아이디"].values:
                        st.error("이미 누군가 사용 중인 아이디입니다. 다른 아이디를 입력해주세요.")
                    elif signup_name in users_df["이름"].values:
                        st.error(f"이미 가입된 '{signup_name}'님의 계정이 존재합니다! 아이디를 잊으셨다면 다시 가입할 수 없습니다.")
                    else:
                        hashed_pw = hash_password(signup_pw)
                        new_user = {"이름": signup_name, "아이디": signup_id, "비밀번호": hashed_pw, "스티커": 0}
                        
                        users_df = pd.concat([users_df, pd.DataFrame([new_user])], ignore_index=True)
                        update_data("회원", users_df) 
                        st.success("🎉 회원가입이 완료되었습니다! 아래의 로그인 버튼을 눌러주세요.")
                else:
                    st.warning("빈칸을 모두 채워주세요.")
                    
        st.write("")
        if st.button("이미 계정이 있으신가요? 🔐 로그인 하기", use_container_width=True):
            st.session_state.auth_mode = "login"
            st.rerun()
            
    st.stop()


# ==========================================
# 앱 공통 상단바
# ==========================================
col_left, col_mid, col_right = st.columns([4, 2, 2])
with col_left:
    st.write(f"반갑습니다, **{st.session_state.current_user}**님! 👋")
with col_mid:
    if st.session_state.page != "selection":
        if st.button("🏠 홈으로", use_container_width=True):
            st.session_state.page = "selection"
            st.rerun()
with col_right:
    if st.button("🚪 로그아웃", use_container_width=True):
        if has_cookies:
            controller.remove("auto_login_user") 
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.session_state.auth_mode = "login"
        st.rerun()
st.divider()


# ==========================================
# [화면 1] 사용자 선택 첫 화면
# ==========================================
if st.session_state.page == "selection":
    st.title("👋 누구의 쿠폰 지갑을 열어볼까요?")
    st.write("")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👦 지현 지갑 보기", use_container_width=True, type="primary"):
            st.session_state.selected_user = "지현"
            st.session_state.page = "wallet"
            st.rerun()
    with col2:
        if st.button("👧 세연 지갑 보기", use_container_width=True, type="primary"):
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
# [화면 1.5] 독립된 칭찬 스티커 판 페이지
# ==========================================
elif st.session_state.page == "sticker_board":
    wallet_owner = st.session_state.selected_user
    viewer = st.session_state.current_user
    
    if st.button("⬅️ 쿠폰 지갑으로 돌아가기"):
        st.session_state.page = "wallet"
        st.rerun()
        
    st.title(f"🌟 {wallet_owner}의 칭찬 스티커 판")
    st.write("예쁜 짓을 할 때마다 도장을 쾅쾅 찍어주세요!")
    st.divider()
    
    owner_idx_list = users_df.index[users_df['이름'] == wallet_owner].tolist()
    if owner_idx_list:
        owner_idx = owner_idx_list[0]
        try:
            sticker_count = int(users_df.at[owner_idx, "스티커"])
        except:
            sticker_count = 0
    else:
        owner_idx = None
        sticker_count = 0
        
    st.write(f"현재 모은 도장: **{sticker_count} / 10 개**")
    st.markdown(f"<h3 style='letter-spacing: 5px; text-align: center; padding: 20px 0;'>{'💖' * sticker_count}{'🤍' * (10 - sticker_count)}</h3>", unsafe_allow_html=True)
    st.write("")

    if viewer == wallet_owner:
        st.info("💡 본인의 도장판은 구경만 할 수 있습니다. 도장은 상대방만 찍어줄 수 있어요!")
    elif owner_idx is None:
        st.error(f"🚨 아직 {wallet_owner}님이 회원가입을 하지 않았어요! {wallet_owner}님이 자신의 계정을 만들어야 스티커를 찍어줄 수 있습니다.")
    else:
        if sticker_count < 10:
            if st.button(f"👍 {wallet_owner}에게 칭찬 도장 쾅!", use_container_width=True, type="primary"):
                users_df.at[owner_idx, "스티커"] = sticker_count + 1
                update_data("회원", users_df)
                st.balloons()
                st.rerun()
        else:
            st.success(f"🎉 짝짝짝! {wallet_owner}님이 칭찬 스티커를 다 모았습니다! 보상 쿠폰을 내려주세요!")
            with st.form("reward_form"):
                reward_name = st.text_input("보상 쿠폰 이름 (이름 앞에 [🌟칭찬보상]이 자동 생성됩니다)")
                reward_benefit = st.text_input("보상 혜택")
                if st.form_submit_button("보상 쿠폰 발급 & 스티커 판 비우기", type="primary"):
                    if reward_name and reward_benefit:
                        now = datetime.now()
                        expire_str = (now + pd.DateOffset(months=3)).strftime("%Y-%m-%d")
                        new_row = {
                            "쿠폰명": f"[🌟칭찬보상] {reward_name}",
                            "혜택": reward_benefit,
                            "상태": "미사용",
                            "생성일": now.strftime("%Y-%m-%d"),
                            "소유자": wallet_owner,
                            "만료일": expire_str,
                            "사용일": "",
                            "메모": ""
                        }
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        update_data("쿠폰", df)
                        
                        users_df.at[owner_idx, "스티커"] = 0
                        update_data("회원", users_df)
                        
                        st.success("보상 쿠폰 발급 완료! 지갑으로 돌아가서 확인해보세요.")
                        st.rerun()
                    else:
                        st.warning("이름과 혜택을 모두 입력해주세요.")


# ==========================================
# [화면 2] 개인 쿠폰 지갑
# ==========================================
elif st.session_state.page == "wallet":
    wallet_owner = st.session_state.selected_user
    
    col_title, col_btn = st.columns([3, 2])
    with col_title:
        st.title(f"🎫 {wallet_owner}의 지갑")
    with col_btn:
        st.write("") 
        if st.button("🌟 칭찬 스티커 판 가기", use_container_width=True):
            st.session_state.page = "sticker_board"
            st.rerun()
    st.divider()
    
    user_df = df[df["소유자"] == wallet_owner]
    active_count = len(user_df[user_df["상태"] == "미사용"])

    st.write(f"현재 쓸 수 있는 쿠폰: **{active_count} / 10 개** (최대 10개)")

    if user_df.empty:
        st.info("현재 지갑이 텅 비어있습니다. 쿠폰을 발급해보세요!")
    else:
        for index, row in user_df.iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                
                exp_date = row.get("만료일", "제한 없음")
                if pd.isna(exp_date) or exp_date == "": 
                    exp_date = "제한 없음"

                with col1:
                    st.subheader(row["쿠폰명"])
                    if row["상태"] == "사용완료" and pd.notna(row.get("사용일")) and row["사용일"] != "":
                        st.caption(f"발급일: {row['생성일']} | **사용일: {row['사용일']}**")
                    else:
                        st.caption(f"발급일: {row['생성일']} | **만료일: {exp_date}**")
                        
                with col2:
                    st.write(f"🎁 **혜택:** {row['혜택']}")
                    if row["상태"] == "미사용":
                        st.success("🟢 미사용")
                    else:
                        st.button("🔴 사용완료", disabled=True, key=f"btn_{index}") 
                with col3:
                    if row["상태"] == "미사용":
                        if st.button("사용하기", key=f"use_{index}", type="primary"):
                            df.at[index, "상태"] = "사용완료"
                            df.at[index, "사용일"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                            update_data("쿠폰", df) 
                            st.balloons() 
                            st.rerun()
                    else:
                        if st.button("되돌리기", key=f"unuse_{index}"):
                            df.at[index, "상태"] = "미사용"
                            df.at[index, "사용일"] = "" 
                            update_data("쿠폰", df) 
                            st.rerun()
                            
                with st.expander("📝 추억 메모장"):
                    memo_val = row.get("메모", "")
                    if pd.isna(memo_val): 
                        memo_val = ""
                    m_col1, m_col2 = st.columns([4, 1])
                    with m_col1:
                        new_memo = st.text_input("메모", value=memo_val, key=f"memo_{index}", placeholder="어디서 어떻게 썼는지 기록해보세요!", label_visibility="collapsed")
                    with m_col2:
                        if st.button("저장", key=f"save_memo_{index}"):
                            df.at[index, "메모"] = new_memo
                            update_data("쿠폰", df) 
                            st.success("저장 완료!")
                            st.rerun()
                
                if row["상태"] == "미사용":
                    with st.expander("✏️ 쿠폰 수정하기"):
                        with st.form(key=f"edit_form_{index}"):
                            edit_name = st.text_input("쿠폰 이름", value=row["쿠폰명"])
                            edit_benefit = st.text_input("쿠폰 혜택", value=row["혜택"])
                            edit_expire = st.text_input("만료일 (YYYY-MM-DD)", value=str(row.get("만료일", "제한 없음")))
                            
                            if st.form_submit_button("수정 내용 저장"):
                                if edit_name and edit_benefit:
                                    df.at[index, "쿠폰명"] = edit_name
                                    df.at[index, "혜택"] = edit_benefit
                                    df.at[index, "만료일"] = edit_expire
                                    update_data("쿠폰", df) 
                                    st.success("수정 완료!")
                                    st.rerun()
                                else:
                                    st.warning("이름과 혜택을 모두 적어주세요.")


# ==========================================
# [화면 3] 통합 쿠폰 관리소 
# ==========================================
elif st.session_state.page == "admin":
    st.title("⚙️ 전체 쿠폰 관리소")
    st.write("새로운 쿠폰을 발급하거나 내역을 관리합니다.")
    st.write("")

    target_user = st.radio("누구의 쿠폰을 조작하시겠습니까?", ["지현", "세연"], horizontal=True)
    target_df = df[df["소유자"] == target_user]
    active_count = len(target_df[target_df["상태"] == "미사용"])

    tab1, tab2, tab3 = st.tabs(["➕ 상세 발급", "⚡ 빠른 발급", "📜 내역 & 삭제"])

    # --- 탭 1: 상세 설정 발급 ---
    with tab1:
        st.subheader(f"{target_user}님 상세 쿠폰 만들기 (현재 남은 칸: {10 - active_count}개)")
        if active_count >= 10:
            st.error("🚨 사용 가능한 쿠폰이 10개가 넘어 더 발급할 수 없습니다!")
        else:
            with st.form(f"new_coupon_form", clear_on_submit=True):
                new_name = st.text_input("쿠폰 이름")
                new_benefit = st.text_input("쿠폰 혜택")
                
                expire_option = st.radio("유효기간 설정", ["1개월", "3개월", "6개월", "직접 설정"], horizontal=True)
                custom_date = st.date_input("직접 설정 (위에서 '직접 설정' 선택 시 적용)")
                
                submitted = st.form_submit_button("발급하기")
                
                if submitted:
                    if new_name and new_benefit:
                        now = datetime.now()
                        if expire_option == "1개월":
                            expire_date = now + pd.DateOffset(months=1)
                        elif expire_option == "3개월":
                            expire_date = now + pd.DateOffset(months=3)
                        elif expire_option == "6개월":
                            expire_date = now + pd.DateOffset(months=6)
                        else:
                            expire_date = pd.to_datetime(custom_date)
                            
                        expire_str = expire_date.strftime("%Y-%m-%d")

                        new_row = {
                            "쿠폰명": new_name,
                            "혜택": new_benefit,
                            "상태": "미사용",
                            "생성일": now.strftime("%Y-%m-%d"),
                            "소유자": target_user,
                            "만료일": expire_str,
                            "사용일": "",
                            "메모": ""
                        }
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        update_data("쿠폰", df) 
                        st.success(f"'{new_name}' 쿠폰 발급 완료! (만료일: {expire_str})")
                        st.rerun()
                    else:
                        st.warning("이름과 혜택을 모두 적어주세요.")

    # --- 탭 2: 빠른 발급 (원클릭 + 재발급) ---
    with tab2:
        st.subheader("⚡ 기본 프리셋 발급")
        st.caption("아래에서 유효기간을 먼저 선택하고 버튼을 누르세요.")
        
        quick_expire_option = st.radio("빠른 발급 유효기간 설정", ["1개월", "3개월", "6개월", "직접 설정"], horizontal=True, key="quick_expire")
        quick_custom_date = st.date_input("직접 설정 (위에서 '직접 설정' 선택 시 적용)", key="quick_custom")
        st.write("") 
        
        presets = [
            {"이름": "🍽️ 원하는 메뉴 먹어주기", "혜택": "상대방이 원하는 메뉴 군말 없이 같이 먹어주기"},
            {"이름": "🧃 음료수 사주기", "혜택": "원하는 음료수 사다 바치기"},
            {"이름": "🛡️ 상대 쿠폰 방어", "혜택": "상대방이 쓰는 쿠폰 1회 무효화 하기 (절대 방어!)"},
            {"이름": "🚗 집 데려다 주기", "혜택": "안전하고 편안하게 집까지 데려다 주기"}
        ]
        
        for p in presets:
            if st.button(f"➕ {p['이름']} 발급", use_container_width=True):
                if active_count >= 10:
                    st.error("쿠폰함이 가득 찼습니다!")
                else:
                    now = datetime.now()
                    if quick_expire_option == "1개월":
                        expire_date = now + pd.DateOffset(months=1)
                    elif quick_expire_option == "3개월":
                        expire_date = now + pd.DateOffset(months=3)
                    elif quick_expire_option == "6개월":
                        expire_date = now + pd.DateOffset(months=6)
                    else:
                        expire_date = pd.to_datetime(quick_custom_date)
                        
                    expire_str = expire_date.strftime("%Y-%m-%d")
                    
                    new_row = {
                        "쿠폰명": p["이름"],
                        "혜택": p["혜택"],
                        "상태": "미사용",
                        "생성일": now.strftime("%Y-%m-%d"),
                        "소유자": target_user,
                        "만료일": expire_str,
                        "사용일": "",
                        "메모": ""
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    update_data("쿠폰", df) 
                    st.success(f"'{p['이름']}' 쿠폰이 빠른 발급되었습니다! (만료일: {expire_str})")
                    st.rerun()

        st.divider()
        
        st.subheader("♻️ 과거에 쓴 쿠폰 다시 발급하기")
        
        used_df = target_df[target_df["상태"] == "사용완료"]
        
        if used_df.empty:
            st.info("아직 사용한 쿠폰이 없어 다시 발급할 내역이 없습니다.")
        else:
            unique_used_df = used_df.drop_duplicates(subset=["쿠폰명"]).reset_index(drop=True)
            reissue_name = st.selectbox("다시 발급할 쿠폰 선택", unique_used_df["쿠폰명"].tolist())
            
            if st.button("♻️ 선택한 쿠폰 재발급", use_container_width=True, type="secondary"):
                if active_count >= 10:
                    st.error("쿠폰함이 가득 찼습니다!")
                else:
                    reissue_benefit = unique_used_df[unique_used_df["쿠폰명"] == reissue_name].iloc[0]["혜택"]
                    
                    now = datetime.now()
                    if quick_expire_option == "1개월":
                        expire_date = now + pd.DateOffset(months=1)
                    elif quick_expire_option == "3개월":
                        expire_date = now + pd.DateOffset(months=3)
                    elif quick_expire_option == "6개월":
                        expire_date = now + pd.DateOffset(months=6)
                    else:
                        expire_date = pd.to_datetime(quick_custom_date)
                        
                    expire_str = expire_date.strftime("%Y-%m-%d")
                    
                    new_row = {
                        "쿠폰명": reissue_name,
                        "혜택": reissue_benefit,
                        "상태": "미사용",
                        "생성일": now.strftime("%Y-%m-%d"),
                        "소유자": target_user,
                        "만료일": expire_str,
                        "사용일": "",
                        "메모": ""
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    update_data("쿠폰", df) 
                    st.success(f"'{reissue_name}' 쿠폰이 다시 발급되었습니다! (만료일: {expire_str})")
                    st.rerun()

    # --- 탭 3: 사용 내역 및 삭제 ---
    with tab3:
        st.subheader("📜 사용 내역")
        used_df = target_df[target_df["상태"] == "사용완료"]
        if used_df.empty:
            st.info("아직 사용한 쿠폰이 없습니다.")
        else:
            st.dataframe(used_df[["쿠폰명", "혜택", "생성일", "사용일", "메모"]], use_container_width=True, hide_index=True)
            
        st.divider()
        st.subheader("🗑️ 기존 쿠폰 영구 삭제")
        st.caption("삭제할 쿠폰을 여러 개 선택해서 한 번에 지울 수 있습니다.")
        
        if target_df.empty:
            st.text("삭제할 쿠폰이 없습니다.")
        else:
            delete_options = {idx: f"{row['쿠폰명']} (상태: {row['상태']}, 발급일: {row['생성일']})" for idx, row in target_df.iterrows()}
            
            selected_del_idxs = st.multiselect("삭제할 쿠폰들을 모두 선택하세요", options=list(delete_options.keys()), format_func=lambda x: delete_options[x])
            
            if st.button("선택한 쿠폰 일괄 삭제", type="primary"):
                if selected_del_idxs: 
                    df = df.drop(selected_del_idxs)
                    update_data("쿠폰", df) 
                    st.success(f"{len(selected_del_idxs)}개의 쿠폰이 깔끔하게 영구 삭제되었습니다.")
                    st.rerun()
                else:
                    st.warning("삭제할 쿠폰을 먼저 선택해주세요.")
