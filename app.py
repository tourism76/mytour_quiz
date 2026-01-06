import time
import uuid
import streamlit as st
from dataclasses import dataclass
from typing import List, Optional

# ----------------------------
# 1. Supabase 연결 설정 (에러 방지형)
# ----------------------------
def get_supabase_client():
    try:
        from supabase import create_client
        if "supabase_url" in st.secrets and "supabase_key" in st.secrets:
            return create_client(st.secrets["supabase_url"], st.secrets["supabase_key"])
        return None
    except Exception:
        return None

sb = get_supabase_client()

# ----------------------------
# 2. 문제 및 데이터 설정
# ----------------------------
@dataclass
class Q:
    prompt: str
    choices: List[str]
    answer_index: int
    difficulty: str 
    img_url: Optional[str] = None 

# 퀴즈 데이터셋
QUESTIONS: List[Q] = [
    Q("파리를 상징하는 가장 유명한 철탑의 이름은?", ["에펠탑", "도쿄타워", "남산타워", "피사의사탑"], 0, "초급", "https://images.unsplash.com/photo-1511739001486-6bfe10ce7859?w=400&q=80"),
    Q("세계 3대 박물관 중 하나로, 유리 피라미드가 있는 곳은?", ["루브르 박물관", "대영 박물관", "바티칸 박물관", "오르세 미술관"], 0, "초급", "https://images.unsplash.com/photo-1499856871940-a09627c6dcf6?w=400&q=80"),
    Q("나폴레옹이 승리를 기념하여 만든 거대한 문은?", ["개선문", "독립문", "브란덴부르크 문", "광화문"], 0, "중급", "https://images.unsplash.com/photo-1509439581779-6298f75bf6e5?w=400&q=80"),
    Q("노트르담 대성당 앞 광장에 있으며, 거리 측정의 기준점이 되는 이것은?", ["포앵 제로(Point Zéro)", "센터 포인트", "로즈 라인", "옴팔로스"], 0, "최상급(BOSS)", "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Point_z%C3%A9ro_des_routes_de_France.jpg/320px-Point_z%C3%A9ro_des_routes_de_France.jpg"),
]

# ----------------------------
# 3. 핵심 로직 함수
# ----------------------------
def calc_points(elapsed_sec):
    """10초 내 응답 시 시간에 따른 차등 점수 (최대 1000점)"""
    if elapsed_sec >= 10.0: return 50 # 최소 점수
    p = 1000 * (1.0 - (elapsed_sec / 10.0))
    return int(max(p, 50))

def safe_save(player_id, name, age_group, score, correct_count, current_q):
    if not sb: return 
    
    data = {
        "player_id": str(player_id),
        "name": str(name),
        "age_group": str(age_group),
        "score": int(score),
        "correct_count": int(correct_count),
        "current_q": int(current_q)
    }
    
    try:
        # .upsert()는 '이미 있으면 업데이트, 없으면 삽입'을 한 번에 수행합니다.
        # on_conflict='player_id'를 지정하여 중복 기준을 명확히 합니다.
        sb.table("quiz_players").upsert(data, on_conflict='player_id').execute()
    except Exception as e:
        # 여기서 오류 내용을 상세히 출력하여 원인을 파악합니다.
        print(f"세부 오류 내용: {e}")

def fetch_leaderboard():
    if not sb: return []
    try:
        res = sb.table("quiz_players").select("name, age_group, score").order("score", desc=True).limit(10).execute()
        return res.data
    except:
        return []

# ----------------------------
# 4. 앱 UI 레이아웃
# ----------------------------
st.set_page_config(page_title="T-Quiz Show", page_icon="🌍", layout="centered")

# 세션 상태 초기화
if "player_id" not in st.session_state: st.session_state.player_id = str(uuid.uuid4())
if "step" not in st.session_state: st.session_state.step = "intro"
if "q_idx" not in st.session_state: st.session_state.q_idx = 0
if "score" not in st.session_state: st.session_state.score = 0
if "correct" not in st.session_state: st.session_state.correct = 0

# [화면 1] 메인 인트로
# [화면 1] 메인 인트로
if st.session_state.step == "intro":
    # 업로드한 파일 이름이 main_bg래와 같이 수정!
    st.image("main_bg", use_container_width=True) 
    
    st.title("""🌍 마이투어유니버스 : 티퀴즈(T-Quiz)")
    # ... 이하 동일
    ### "유재석은 '유퀴즈'를 하고, 마이투어유니버스는 '티퀴즈(T-Quiz)'를 합니다!"
    당신의 여행 지식을 뽐내고 실시간 랭킹에 도전하세요. 
    **빨리 맞힐수록 점수가 올라갑니다! (10초 카운트다운)**
    """)
    
    st.divider()
    
    with st.form("register_form"):
        name = st.text_input("닉네임", placeholder="랭킹에 표시될 이름")
        age = st.selectbox("연령대", ["MZ세대", "40대", "50대+"])
        submit = st.form_submit_button("🚀 퀴즈 시작하기")
        
        if submit:
            if name.strip():
                st.session_state.name = name
                st.session_state.age = age
                st.session_state.step = "quiz"
                st.session_state.start_time = time.time()
                safe_save(st.session_state.player_id, name, age, 0, 0, 0)
                st.rerun()
            else:
                st.error("닉네임을 입력해 주세요!")

# [화면 2] 퀴즈 풀이
elif st.session_state.step == "quiz":
    if st.session_state.q_idx >= len(QUESTIONS):
        st.session_state.step = "result"
        st.rerun()

    q = QUESTIONS[st.session_state.q_idx]
    
    # 상단 정보
    col1, col2 = st.columns([2, 1])
    col1.caption(f"문제 {st.session_state.q_idx + 1} / {len(QUESTIONS)}")
    col2.markdown(f"**현재 점수: {st.session_state.score}**")
    
    st.progress((st.session_state.q_idx) / len(QUESTIONS))
    st.subheader(q.prompt)

    # 이미지 크기 최적화 (작게 표시)
    if q.img_url:
        st.markdown(
            f'<div style="display: flex; justify-content: center;">'
            f'<img src="{q.img_url}" style="width: 300px; border-radius: 10px; margin: 10px 0;">'
            f'</div>', 
            unsafe_allow_html=True
        )

    # 타이머 시작 시간 설정
    if "q_start_time" not in st.session_state or st.session_state.q_start_time is None:
        st.session_state.q_start_time = time.time()

    # 정답 선택
    choice = st.radio("보기를 선택하세요", q.choices, index=None, key=f"choice_{st.session_state.q_idx}")

    if st.button("정답 제출 ➡️"):
        if choice:
            elapsed = time.time() - st.session_state.q_start_time
            is_correct = (choice == q.choices[q.answer_index])
            
            if is_correct:
                points = calc_points(elapsed)
                st.session_state.score += points
                st.session_state.correct += 1
                st.success(f"정답입니다! (+{points}점 / 응답시간: {elapsed:.1f}초)")
            else:
                st.error(f"아쉽네요! 정답은 '{q.choices[q.answer_index]}'입니다.")
            
            # 인덱스 증가 및 초기화
            st.session_state.q_idx += 1
            st.session_state.q_start_time = None
            
            # DB 업데이트
            safe_save(st.session_state.player_id, st.session_state.name, st.session_state.age, 
                      st.session_state.score, st.session_state.correct, st.session_state.q_idx)
            
            time.sleep(1.5)
            st.rerun()
        else:
            st.warning("정답을 선택해 주세요!")

# [화면 3] 최종 결과 및 명예의 전당
elif st.session_state.step == "result":
    st.balloons()
    st.title("🏆 T-Quiz 종료!")
    st.markdown(f"## {st.session_state.name} 님의 최종 점수는 **{st.session_state.score}점**입니다.")
    st.write(f"총 {len(QUESTIONS)}문제 중 {st.session_state.correct}문제를 맞히셨습니다.")

    st.divider()
    st.subheader("🏅 실시간 명예의 전당")
    leaderboard = fetch_leaderboard()
    if leaderboard:
        st.table(leaderboard)

    if st.button("다시 도전하기"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()