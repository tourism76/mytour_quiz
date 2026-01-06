import time
import uuid
import streamlit as st
from dataclasses import dataclass
from typing import List, Optional

# ----------------------------
# 1. Supabase 연결 설정
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
# 2. 문제 데이터 (10문제)
# ----------------------------
@dataclass
class Q:
    prompt: str
    choices: List[str]
    answer_index: int
    difficulty: str 
    img_url: Optional[str] = None 

QUESTIONS: List[Q] = [
    Q("파리를 상징하는 가장 유명한 철탑의 이름은?", ["에펠탑", "도쿄타워", "남산타워", "피사의사탑"], 0, "초급", "https://images.unsplash.com/photo-1511739001486-6bfe10ce7859?w=400&q=80"),
    Q("세계 3대 박물관 중 하나로, 유리 피라미드가 있는 곳은?", ["루브르 박물관", "대영 박물관", "바티칸 박물관", "오르세 미술관"], 0, "초급", "https://images.unsplash.com/photo-1499856871940-a09627c6dcf6?w=400&q=80"),
    Q("파리를 관통하여 흐르는 강의 이름은?", ["센강(Seine)", "한강", "템즈강", "다뉴브강"], 0, "초급", "https://images.unsplash.com/photo-1471623320832-752e8bbf8413?w=400&q=80"),
    Q("나폴레옹이 승리를 기념하여 만든 거대한 문은?", ["개선문", "독립문", "브란덴부르크 문", "광화문"], 0, "중급", "https://images.unsplash.com/photo-1509439581779-6298f75bf6e5?w=400&q=80"),
    Q("'오 샹젤리제~' 노래로 유명한 파리의 대표적인 쇼핑 거리는?", ["샹젤리제 거리", "가로수길", "5번가", "옥스포드 스트릿"], 0, "중급", "https://images.unsplash.com/photo-1588669527230-2eb99df89ddc?w=400&q=80"),
    Q("파리 시내를 한눈에 볼 수 있는 하얀 돔 성당이 있는 언덕은?", ["몽마르트 언덕", "남산", "몽생미셸", "에트르타"], 0, "중급", "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=400&q=80"),
    Q("영화 '퐁네프의 연인들' 배경이자 파리에서 가장 오래된 다리는?", ["퐁뇌프(Pont Neuf)", "미라보 다리", "알렉상드르 3세 다리", "퐁데자르"], 0, "상급", "https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/Pont_Neuf%2C_Paris_July_2013.jpg/320px-Pont_Neuf%2C_Paris_July_2013.jpg"),
    Q("파리의 지하철 입구를 아르누보 양식으로 디자인한 건축가는?", ["엑토르 기마르", "구스타브 에펠", "르 코르뷔지에", "가우디"], 0, "상급", "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Metropolitain_Abbesses.jpg/300px-Metropolitain_Abbesses.jpg"),
    Q("오페라의 유령 배경이 된 화려한 오페라 극장의 이름은?", ["오페라 가르니에", "오페라 바스티유", "물랑루즈", "샤틀레 극장"], 0, "상급", "https://images.unsplash.com/photo-1520182604857-4b77f4803529?w=400&q=80"),
    Q("노트르담 대성당 앞 광장에 있는 파리 거리 측정의 기준점은?", ["포앵 제로(Point Zéro)", "센터 포인트", "로즈 라인", "옴팔로스"], 0, "최상급(BOSS)", "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Point_z%C3%A9ro_des_routes_de_France.jpg/320px-Point_z%C3%A9ro_des_routes_de_France.jpg"),
]

def calc_points(elapsed_sec):
    if elapsed_sec >= 10.0: return 50
    p = 1000 * (1.0 - (elapsed_sec / 10.0))
    return int(max(p, 50))

def safe_save(player_id, name, age_group, score, correct_count, current_q):
    if not sb: return 
    data = {"player_id": str(player_id), "name": str(name), "age_group": str(age_group), "score": int(score), "correct_count": int(correct_count), "current_q": int(current_q)}
    try:
        sb.table("quiz_players").upsert(data, on_conflict='player_id').execute()
    except: pass

st.set_page_config(page_title="T-Quiz Show", page_icon="🌍")

if "player_id" not in st.session_state: st.session_state.player_id = str(uuid.uuid4())
if "step" not in st.session_state: st.session_state.step = "intro"
if "q_idx" not in st.session_state: st.session_state.q_idx = 0
if "score" not in st.session_state: st.session_state.score = 0
if "correct" not in st.session_state: st.session_state.correct = 0

if st.session_state.step == "intro":
    # ⚠️ 파일명이 main_bg.png 인지 꼭 확인하세요!
    try:
        st.image("main_bg.png", use_container_width=True)
    except:
        st.error("이미지 파일명을 main_bg.png 로 맞춰주세요!")

    st.title("🌍 마이투어유니버스 : 티퀴즈(T-Quiz)")
    st.markdown("""
    ### "유재석은 '유퀴즈'를 하고, 마이투어유니버스는 '티퀴즈(T-Quiz)'를 합니다!"
    당신의 여행 지식을 뽐내고 실시간 랭킹에 도전하세요.
    **10초 안에 정답을 누를수록 점수가 높아집니다!**
    """)
    
    with st.form("reg"):
        name = st.text_input("닉네임")
        age = st.selectbox("리그", ["MZ세대", "40대", "50대+"])
        if st.form_submit_button("🚀 출발하기"):
            if name.strip():
                st.session_state.name, st.session_state.age = name, age
                st.session_state.step = "quiz"
                st.session_state.q_start_time = time.time()
                st.rerun()

elif st.session_state.step == "quiz":
    if st.session_state.q_idx >= len(QUESTIONS):
        st.session_state.step = "result"
        st.rerun()
    q = QUESTIONS[st.session_state.q_idx]
    st.subheader(f"Q{st.session_state.q_idx+1}. {q.prompt}")
    if q.img_url:
        st.markdown(f'<div style="text-align:center;"><img src="{q.img_url}" style="width:300px; border-radius:10px;"></div>', unsafe_allow_html=True)
    
    if "q_start_time" not in st.session_state: st.session_state.q_start_time = time.time()
    choice = st.radio("정답 선택", q.choices, index=None, key=f"q_{st.session_state.q_idx}")
    if st.button("제출 ➡️"):
        if choice:
            elapsed = time.time() - st.session_state.q_start_time
            if choice == q.choices[q.answer_index]:
                st.session_state.score += calc_points(elapsed)
                st.session_state.correct += 1
            st.session_state.q_idx += 1
            st.session_state.q_start_time = time.time()
            safe_save(st.session_state.player_id, st.session_state.name, st.session_state.age, st.session_state.score, st.session_state.correct, st.session_state.q_idx)
            st.rerun()

elif st.session_state.step == "result":
    st.balloons()
    st.title("🏆 최종 점수: " + str(st.session_state.score) + "점")
    if st.button("다시 하기"):
        st.session_state.clear()
        st.rerun()