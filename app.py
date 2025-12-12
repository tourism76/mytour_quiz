# app.py
import time
import random
from dataclasses import dataclass
from typing import Optional, List, Dict

import streamlit as st
import pandas as pd


# -----------------------------
# 0) 서버 메모리(간단 리더보드)
#    Streamlit Cloud는 "외부 DB" 없으면 재시작/재배포 시 초기화됩니다.
# -----------------------------
@st.cache_resource
def get_store():
    return {
        "players": {},   # player_id -> record
        "lucky_winners": set(),  # 중복 당첨 방지(선택)
    }


# -----------------------------
# 1) 문제 데이터 구조
# -----------------------------
@dataclass
class Question:
    qid: int
    title: str
    prompt: str
    choices: List[str]
    answer_idx: int
    explanation: str
    image_url: Optional[str] = None
    base_max: int = 800   # 난이도/문제별 최대점수(마지막 문제 크게)
    base_min: int = 150   # 1~10초 구간의 최저점수(정답일 때)


def build_questions() -> List[Question]:
    # 이미지 URL은 "예시"입니다. 원하시면 회장님 콘텐츠에 맞게 문제/이미지 세트로 커스터마이징해드릴게요.
    return [
        Question(
            qid=1,
            title="Q1 (워밍업/이미지)",
            prompt="이 국기는 어느 나라일까요?",
            image_url="https://upload.wikimedia.org/wikipedia/en/c/c3/Flag_of_France.svg",
            choices=["이탈리아", "프랑스", "네덜란드", "러시아"],
            answer_idx=1,
            explanation="세로 삼색(파-흰-빨)은 프랑스 국기 트리콜로르!",
            base_max=600, base_min=120
        ),
        Question(
            qid=2,
            title="Q2 (가벼운 상식)",
            prompt="비행기 이륙/착륙 시 가장 기본적으로 안내하는 것은?",
            choices=["기내식 메뉴 선택", "좌석벨트 착용", "면세품 구매", "좌석 등받이 젖히기"],
            answer_idx=1,
            explanation="이륙/착륙 때는 좌석벨트 착용이 기본 안전수칙이에요.",
            base_max=650, base_min=130
        ),
        Question(
            qid=3,
            title="Q3 (체감 난이도↑)",
            prompt="유럽 여행에서 '오버투어리즘'이란 무엇을 뜻할까요?",
            choices=["관광객이 너무 적어 침체된 상태", "관광객이 과도하게 몰려 지역이 과부하된 상태", "투어 비용이 너무 비싼 상태", "야간 투어가 많은 상태"],
            answer_idx=1,
            explanation="관광객 과밀로 주민 삶/환경/인프라에 부담이 커지는 현상입니다.",
            base_max=750, base_min=150
        ),
        Question(
            qid=4,
            title="Q4 (이미지/랜드마크)",
            prompt="이 랜드마크로 가장 유명한 도시는?",
            image_url="https://upload.wikimedia.org/wikipedia/commons/6/6f/Colosseum_in_Rome%2C_Italy_-_April_2007.jpg",
            choices=["로마", "파리", "런던", "비엔나"],
            answer_idx=0,
            explanation="콜로세움은 로마의 상징이죠.",
            base_max=900, base_min=170
        ),
        Question(
            qid=5,
            title="Q5 (여행 꿀지식)",
            prompt="시차 적응(제트랙) 완화에 가장 도움 되는 행동은?",
            choices=["도착 즉시 낮잠 4시간", "도착지 현지시간에 맞춰 햇빛 쬐기", "카페인 많이 마시기", "잠을 아예 안 자기"],
            answer_idx=1,
            explanation="빛(햇빛)은 생체시계를 리셋하는 가장 강력한 신호예요.",
            base_max=950, base_min=180
        ),
        Question(
            qid=6,
            title="Q6 (난이도 중상)",
            prompt="여행상품에서 '랜드 오퍼레이터(Land Operator)'의 역할에 가장 가까운 것은?",
            choices=["항공권만 판매", "현지 일정/차량/가이드/호텔 등 지상수배 총괄", "여행 보험만 판매", "환전만 대행"],
            answer_idx=1,
            explanation="현지에서 굴러가는 대부분을 설계/운영하는 실무 핵심이에요.",
            base_max=1100, base_min=200
        ),
        Question(
            qid=7,
            title="Q7 (논리형)",
            prompt="A도시(2박) → B도시(1박) → A도시(1박) 동선을 줄이면 가장 먼저 바꿀 것은?",
            choices=["식사 횟수", "도시 순서/숙박 분배", "여행자 나이", "환율"],
            answer_idx=1,
            explanation="이건 동선 최적화 문제라 숙박/이동 구조가 1순위예요.",
            base_max=1250, base_min=230
        ),
        Question(
            qid=8,
            title="Q8 (상급/개념)",
            prompt="퀴즈쇼에서 이탈을 줄이기 위한 가장 직접적인 장치는?",
            choices=["문제를 더 어렵게", "중간 체크포인트(순위/보상) 설계", "광고를 더 길게", "질문을 더 길게"],
            answer_idx=1,
            explanation="3/6/9 체크포인트 + 보상(럭키드로우)은 ‘계속 남을 이유’를 줍니다.",
            base_max=1500, base_min=260
        ),
        Question(
            qid=9,
            title="Q9 (상급/승부처 + 럭키드로우 전)",
            prompt="타이머 점수형 퀴즈에서 '반응속도 불만'을 줄이는 확장 전략으로 적절한 것은?",
            choices=["문제 수를 100개로", "연령/리그 분리(예: MZ/50+) 또는 핸디캡", "정답을 공개하지 않기", "버튼을 작게 만들기"],
            answer_idx=1,
            explanation="리그 분리/핸디캡은 공정성 인식을 크게 올려요.",
            base_max=1800, base_min=300
        ),
        Question(
            qid=10,
            title="Q10 (최상급/우승 결정)",
            prompt="다음 중 '동점자'가 발생했을 때 우승자를 더 잘 가르는 타이브레이커로 좋은 것은?",
            choices=["닉네임 길이", "총 소요시간(0.01초 단위) 또는 마지막 문제 응답시간", "나이", "접속 브라우저"],
            answer_idx=1,
            explanation="총 소요시간/마지막 문제 응답시간은 실력 차이를 더 잘 드러냅니다.",
            base_max=2500, base_min=400
        ),
    ]


# -----------------------------
# 2) 점수 함수
# -----------------------------
def calc_points(correct: bool, elapsed: float, max_points: int, min_points: int) -> int:
    """elapsed: 초 단위. 0.01초 단위까지 반영(표시/저장)."""
    if not correct:
        return 0
    if elapsed >= 10.0:
        return 0
    if elapsed < 1.0:
        return max_points
    # 1~10초: 선형 감점(1초에 max, 10초에 min)
    # t=1 -> 0, t=10 -> 1
    t = (elapsed - 1.0) / 9.0
    score = round(max_points - t * (max_points - min_points))
    return int(max(score, min_points))


def now_perf():
    return time.perf_counter()


def format_sec(x: float) -> str:
    return f"{x:.2f}s"


# -----------------------------
# 3) 리더보드
# -----------------------------
def leaderboard_df(store, age_filter: str = "전체"):
    rows = []
    for pid, r in store["players"].items():
        if age_filter != "전체" and r["age_group"] != age_filter:
            continue
        rows.append({
            "닉네임": r["name"],
            "나이대": r["age_group"],
            "점수": r["score"],
            "정답수": r["correct_count"],
            "총시간(정답제출)": round(r["total_time"], 2),
            "진행": f'{r["current_q"]}/10',
        })
    if not rows:
        return pd.DataFrame(columns=["닉네임","나이대","점수","정답수","총시간(정답제출)","진행"])
    df = pd.DataFrame(rows)
    # 점수 내림차순, 총시간 오름차순(빨리 정확히 푼 사람 우위)
    df = df.sort_values(by=["점수", "총시간(정답제출)"], ascending=[False, True]).reset_index(drop=True)
    df.index = df.index + 1
    df.insert(0, "순위", df.index)
    return df


def get_rank(df: pd.DataFrame, name: str):
    if df.empty:
        return None
    hit = df.index[df["닉네임"] == name].tolist()
    return int(df.loc[hit[0], "순위"]) if hit else None


# -----------------------------
# 4) Streamlit UI
# -----------------------------
st.set_page_config(page_title="타이머 퀴즈 (Streamlit)", layout="centered")

store = get_store()
questions = build_questions()

st.title("🌍 타이머 퀴즈 (10문제)")

with st.expander("운영 흐름(15분 설계) / 규칙", expanded=False):
    st.write(
        "- 인트로+안내 2~3분 → 10문제 10~15분 → 우승 발표/엔딩 2~3분\n"
        "- 점수: 1초 미만 최대 / 10초 미만 감점 / 10초 이상 0점\n"
        "- 3/6/9번 종료 후: 전체 순위 + 내 순위 표시\n"
        "- 9번 후: 럭키드로우(간단 버전)\n"
        "- 확장: MZ/50+ 리그 분리 또는 핸디캡 가능"
    )

# 세션 초기화
if "started" not in st.session_state:
    st.session_state.started = False
if "player_id" not in st.session_state:
    st.session_state.player_id = None
if "q_index" not in st.session_state:
    st.session_state.q_index = 0
if "q_start_t" not in st.session_state:
    st.session_state.q_start_t = None
if "answered" not in st.session_state:
    st.session_state.answered = False
if "last_elapsed" not in st.session_state:
    st.session_state.last_elapsed = None
if "last_points" not in st.session_state:
    st.session_state.last_points = 0
if "last_correct" not in st.session_state:
    st.session_state.last_correct = False
if "show_checkpoint" not in st.session_state:
    st.session_state.show_checkpoint = False
if "checkpoint_at" not in st.session_state:
    st.session_state.checkpoint_at = None


def ensure_player(name: str, age_group: str):
    pid = f"{name}:{age_group}"
    st.session_state.player_id = pid
    if pid not in store["players"]:
        store["players"][pid] = {
            "name": name,
            "age_group": age_group,
            "score": 0,
            "correct_count": 0,
            "total_time": 0.0,   # 정답 제출까지 걸린 시간 누적(타이브레이커)
            "current_q": 0,      # 0~10
        }
    return pid


# -----------------------------
# 시작 화면
# -----------------------------
if not st.session_state.started:
    st.subheader("🎬 참가자 등록")
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("닉네임", value="", placeholder="예: 행자언니팬01")
    with c2:
        age_group = st.selectbox("리그(나이대)", ["전체", "MZ", "50+"], index=1)

    st.caption("※ 리그를 '전체'로 두면 통합 순위, MZ/50+로 두면 분리 순위처럼 운용 가능합니다.")

    if st.button("퀴즈 시작", type="primary", disabled=(len(name.strip()) < 2)):
        pid = ensure_player(name.strip(), age_group)
        st.session_state.started = True
        st.session_state.q_index = 0
        st.session_state.q_start_t = None
        st.session_state.answered = False
        st.session_state.show_checkpoint = False
        st.rerun()

    st.stop()


# 참가자 정보
player = store["players"][st.session_state.player_id]
st.write(f"👤 **{player['name']}** / 리그: **{player['age_group']}**")
st.metric("현재 점수", player["score"])
st.metric("진행", f"{player['current_q']}/10")

# 리더보드 필터(운영자/참가자 공용)
age_filter = st.selectbox("리더보드 보기", ["전체", "MZ", "50+"], index=0)
df_lb = leaderboard_df(store, age_filter=age_filter)

# -----------------------------
# 체크포인트 표시(3/6/9 이후)
# -----------------------------
def show_leaderboard_block(title: str):
    st.subheader(title)
    if df_lb.empty:
        st.info("아직 순위 데이터가 없습니다.")
        return
    my_rank = get_rank(df_lb, player["name"])
    st.dataframe(df_lb, use_container_width=True, hide_index=True)
    if my_rank is not None:
        st.success(f"현재 **내 순위: {my_rank}위** (필터: {age_filter})")
    else:
        st.warning("내 닉네임이 리더보드에서 보이지 않아요(필터를 '전체'로 바꿔보세요).")


if st.session_state.show_checkpoint:
    cp = st.session_state.checkpoint_at
    show_leaderboard_block(f"🏁 체크포인트 리더보드 (Q{cp} 종료)")
    if cp == 9:
        st.markdown("### 🎁 럭키드로우 (Q9 종료 보너스)")
        st.caption("간단 버전: 현재 서버에 기록된 참가자 중 1명 랜덤 추첨(리그 필터 적용).")
        eligible_df = df_lb.copy()
        if eligible_df.empty:
            st.info("추첨할 참가자가 없습니다.")
        else:
            if st.button("럭키드로우 뽑기 🎲"):
                # 이미 당첨된 닉네임 제외(선택)
                pool = [n for n in eligible_df["닉네임"].tolist() if n not in store["lucky_winners"]]
                if not pool:
                    st.warning("모든 참가자가 이미 당첨된 상태입니다(서버 기준).")
                else:
                    winner = random.choice(pool)
                    store["lucky_winners"].add(winner)
                    st.success(f"🎉 당첨자: **{winner}**")
                    st.write("이제 마지막 Q10으로 우승자를 결정지어봅시다.")
    if st.button("문제 계속하기 ▶"):
        st.session_state.show_checkpoint = False
        st.session_state.checkpoint_at = None
        st.rerun()


# -----------------------------
# 퀴즈 본게임
# -----------------------------
q_idx = st.session_state.q_index

# 종료 처리
if q_idx >= len(questions):
    st.subheader("🏆 퀴즈 종료!")
    show_leaderboard_block("최종 리더보드")
    st.balloons()
    if st.button("처음으로(다시 참가)"):
        st.session_state.started = False
        st.session_state.player_id = None
        st.rerun()
    st.stop()

q = questions[q_idx]
st.subheader(q.title)
st.write(q.prompt)

if q.image_url:
    st.image(q.image_url, caption="이미지 문제", use_container_width=True)

# 문제 시작 타이머 세팅(최초 표시 때만)
if st.session_state.q_start_t is None or player["current_q"] != (q_idx):
    st.session_state.q_start_t = now_perf()

# 선택지
choice = st.radio(
    "정답을 선택하세요",
    options=list(range(len(q.choices))),
    format_func=lambda i: q.choices[i],
    key=f"choice_{q.qid}",
    disabled=st.session_state.answered,
)

# 제출 버튼
submit = st.button("제출", type="primary", disabled=st.session_state.answered)

if submit:
    elapsed = now_perf() - st.session_state.q_start_t
    elapsed = round(elapsed, 2)  # 0.01초 단위
    correct = (choice == q.answer_idx)

    pts = calc_points(correct, elapsed, q.base_max, q.base_min)

    # 플레이어 기록 업데이트
    if correct:
        player["score"] += pts
        player["correct_count"] += 1
        player["total_time"] += elapsed  # 타이브레이커
    player["current_q"] = q_idx + 1

    # 세션 기록
    st.session_state.answered = True
    st.session_state.last_elapsed = elapsed
    st.session_state.last_points = pts
    st.session_state.last_correct = correct

# 제출 결과 표시
if st.session_state.answered:
    elapsed = st.session_state.last_elapsed
    correct = st.session_state.last_correct
    pts = st.session_state.last_points

    st.write("---")
    st.write(f"⏱️ 응답시간: **{format_sec(elapsed)}**")
    if correct:
        st.success(f"✅ 정답! +{pts}점")
    else:
        st.error("❌ 오답! (이번 문제 점수 0점)")
        st.info(f"정답: **{q.choices[q.answer_idx]}**")

    with st.expander("해설 보기", expanded=True):
        st.write(q.explanation)

    # 다음 문제
    if st.button("다음 문제 ▶"):
        # 체크포인트: 3/6/9에서 리더보드 띄우기
        next_q_num = q_idx + 1
        if next_q_num in [3, 6, 9]:
            st.session_state.show_checkpoint = True
            st.session_state.checkpoint_at = next_q_num
        st.session_state.q_index += 1
        st.session_state.q_start_t = None
        st.session_state.answered = False
        st.rerun()
else:
    st.caption("정답 선택 후 '제출'을 누르면 시간 기반 점수가 계산됩니다.")
