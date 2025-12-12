import os
import time
import uuid
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

# -----------------------------
# Optional: Supabase client
# -----------------------------
SUPABASE_AVAILABLE = False
try:
    from supabase import create_client  # pip install supabase
    SUPABASE_AVAILABLE = True
except Exception:
    SUPABASE_AVAILABLE = False


# =============================
# Quiz: Paris only (10 questions)
# 난이도: 1 -> 10
# =============================
QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "difficulty": 1,
        "type": "image",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/a/a8/Tour_Eiffel_Wikimedia_Commons.jpg",
        "question": "이 사진 속 랜드마크는?",
        "options": ["개선문", "에펠탑", "루브르 피라미드", "몽파르나스 타워"],
        "answer": 1,
        "base_points": 200,
    },
    {
        "id": 2,
        "difficulty": 2,
        "type": "mcq",
        "question": "파리의 대표적인 강은?",
        "options": ["라인강", "센강(Seine)", "다뉴브강", "포강"],
        "answer": 1,
        "base_points": 250,
    },
    {
        "id": 3,
        "difficulty": 3,
        "type": "mcq",
        "question": "루브르 박물관의 상징으로 유명한 유리 구조물은?",
        "options": ["유리 돔", "유리 피라미드", "유리 다리", "유리 타워"],
        "answer": 1,
        "base_points": 300,
    },
    {
        "id": 4,
        "difficulty": 4,
        "type": "mcq",
        "question": "몽마르트 언덕 위에 있는 하얀 대성당은?",
        "options": ["노트르담 대성당", "생트샤펠", "사크레쾨르 대성당", "생제르맹데프레 성당"],
        "answer": 2,
        "base_points": 380,
    },
    {
        "id": 5,
        "difficulty": 5,
        "type": "mcq",
        "question": "개선문(Arc de Triomphe)이 위치한 광장(또는 로터리)로 가장 잘 알려진 곳은?",
        "options": ["콩코르드 광장", "바스티유 광장", "샤를 드골 광장(에투알)", "보주 광장"],
        "answer": 2,
        "base_points": 450,
    },
    {
        "id": 6,
        "difficulty": 6,
        "type": "mcq",
        "question": "파리 지하철(Métro) 노선도에서 흔히 쓰는 색은 노선별로 다르지만, 표지판/안내에 자주 등장하는 대표색 조합은?",
        "options": ["검정/노랑", "파랑/하양", "초록/보라", "빨강/주황"],
        "answer": 1,
        "base_points": 520,
    },
    {
        "id": 7,
        "difficulty": 7,
        "type": "mcq",
        "question": "파리의 '라탱 지구(Quartier Latin)'는 전통적으로 무엇과 연관이 깊을까?",
        "options": ["대형 공항", "대학/학문/학생 문화", "항구 물류", "스키 리조트"],
        "answer": 1,
        "base_points": 600,
    },
    {
        "id": 8,
        "difficulty": 8,
        "type": "mcq",
        "question": "오르세 미술관(Musée d'Orsay)은 원래 어떤 용도로 지어진 건물일까?",
        "options": ["기차역", "왕궁", "성당", "극장"],
        "answer": 0,
        "base_points": 700,
    },
    {
        "id": 9,
        "difficulty": 9,
        "type": "mcq",
        "question": "파리의 행정구역 '아롱디스망(arrondissement)'은 총 몇 개일까?",
        "options": ["10개", "12개", "16개", "20개"],
        "answer": 3,
        "base_points": 850,
    },
    {
        "id": 10,
        "difficulty": 10,
        "type": "mcq",
        "question": "파리의 유명한 묘지 '페르 라셰즈(Père Lachaise)'가 특히 유명한 이유로 가장 적절한 것은?",
        "options": ["유럽 최대의 테마파크가 있다", "유명 인물들의 묘가 다수 있다", "파리에서 가장 높은 전망대가 있다", "세계 최대의 쇼핑몰이 있다"],
        "answer": 1,
        "base_points": 1000,
    },
]

CHECKPOINTS = {3, 6, 9}  # 문제 번호 기준


# =============================
# Scoring
# - <1초: 최대점수
# - 1~<10초: 선형 감소(10초에 가까울수록 낮음)
# - >=10초: 0점
# =============================
def time_multiplier(elapsed_sec: float) -> float:
    if elapsed_sec < 1.0:
        return 1.0
    if elapsed_sec < 10.0:
        # elapsed=1 => 1.0, elapsed=10 => 0.1
        return 0.1 + (10.0 - elapsed_sec) * (0.9 / 9.0)
    return 0.0


# =============================
# Storage (Memory / Supabase)
# =============================
@dataclass
class Player:
    player_id: str
    name: str
    age_group: str
    score: float = 0.0
    correct_count: int = 0
    total_time: float = 0.0
    current_q: int = 0  # 0~10
    updated_at: float = 0.0


@st.cache_resource
def _memory_db() -> Dict[str, Any]:
    return {
        "players": {},   # player_id -> Player
        "winners": [],   # list of dict
        "lucky_draw_lock": False,
        "lucky_draw_winner": None,
        "lucky_draw_ts": None,
    }


class MemoryStore:
    def __init__(self):
        self.db = _memory_db()

    def init_player(self, p: Player) -> None:
        p.updated_at = time.time()
        self.db["players"][p.player_id] = p

    def upsert_player(self, p: Player) -> None:
        p.updated_at = time.time()
        self.db["players"][p.player_id] = p

    def get_leaderboard(self, limit: int = 50) -> List[Player]:
        players = list(self.db["players"].values())
        players.sort(key=lambda x: (-x.score, x.total_time, -x.correct_count, x.updated_at))
        return players[:limit]

    def get_player(self, player_id: str) -> Optional[Player]:
        return self.db["players"].get(player_id)

    def lucky_draw(self) -> Dict[str, Any]:
        # 1시간 내 이미 추첨됐으면 재사용
        now = time.time()
        if self.db["lucky_draw_winner"] and self.db["lucky_draw_ts"] and (now - self.db["lucky_draw_ts"] < 3600):
            return self.db["lucky_draw_winner"]

        eligible = [p for p in self.db["players"].values() if p.current_q >= 9]
        if not eligible:
            raise RuntimeError("아직 추첨 대상(9번 이상 완료)이 없습니다.")

        winner = random.choice(eligible)
        result = {
            "winner_name": winner.name,
            "age_group": winner.age_group,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.db["lucky_draw_winner"] = result
        self.db["lucky_draw_ts"] = now
        self.db["winners"].append(result)
        return result

    def get_winners(self, limit: int = 10) -> List[Dict[str, Any]]:
        return list(reversed(self.db["winners"]))[:limit]


class SupabaseStore:
    def __init__(self, url: str, key: str):
        if not SUPABASE_AVAILABLE:
            raise RuntimeError("supabase 패키지가 설치되어 있지 않습니다. requirements.txt에 supabase를 추가하세요.")
        self.sb = create_client(url, key)

    def init_player(self, p: Player) -> None:
        # 참가자 등록 즉시 1줄 생성(핵심: row가 안생기는 문제를 여기서 바로 잡음)
        payload = {
            "player_id": p.player_id,
            "name": p.name,
            "age_group": p.age_group,
            "score": float(p.score),
            "correct_count": int(p.correct_count),
            "total_time": float(p.total_time),
            "current_q": int(p.current_q),
        }
        self.sb.table("quiz_players").upsert(payload).execute()

    def upsert_player(self, p: Player) -> None:
        payload = {
            "player_id": p.player_id,
            "name": p.name,
            "age_group": p.age_group,
            "score": float(p.score),
            "correct_count": int(p.correct_count),
            "total_time": float(p.total_time),
            "current_q": int(p.current_q),
        }
        self.sb.table("quiz_players").upsert(payload).execute()

    def get_player(self, player_id: str) -> Optional[Player]:
        res = self.sb.table("quiz_players").select("*").eq("player_id", player_id).limit(1).execute()
        data = res.data or []
        if not data:
            return None
        r = data[0]
        return Player(
            player_id=r["player_id"],
            name=r.get("name", ""),
            age_group=r.get("age_group", ""),
            score=float(r.get("score", 0) or 0),
            correct_count=int(r.get("correct_count", 0) or 0),
            total_time=float(r.get("total_time", 0) or 0),
            current_q=int(r.get("current_q", 0) or 0),
            updated_at=time.time(),
        )

    def get_leaderboard(self, limit: int = 50) -> List[Player]:
        # 점수 desc, 총시간 asc (동점이면 더 빨리 푼 사람이 우위)
        res = (
            self.sb.table("quiz_players")
            .select("*")
            .order("score", desc=True)
            .order("total_time", desc=False)
            .order("correct_count", desc=True)
            .limit(limit)
            .execute()
        )
        rows = res.data or []
        out: List[Player] = []
        for r in rows:
            out.append(
                Player(
                    player_id=r["player_id"],
                    name=r.get("name", ""),
                    age_group=r.get("age_group", ""),
                    score=float(r.get("score", 0) or 0),
                    correct_count=int(r.get("correct_count", 0) or 0),
                    total_time=float(r.get("total_time", 0) or 0),
                    current_q=int(r.get("current_q", 0) or 0),
                    updated_at=time.time(),
                )
            )
        return out

    def lucky_draw(self) -> Dict[str, Any]:
        # 최근 1시간 내 이미 winner가 있으면 그걸 반환(중복 추첨 방지)
        try:
            recent = (
                self.sb.table("quiz_lucky_winners")
                .select("*")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = recent.data or []
            if rows:
                # created_at이 문자열/타임스탬프일 수 있어서 널널하게 처리
                return {
                    "winner_name": rows[0].get("winner_name", ""),
                    "age_group": rows[0].get("age_group", ""),
                    "created_at": str(rows[0].get("created_at", "")),
                }
        except Exception:
            pass

        eligible = (
            self.sb.table("quiz_players")
            .select("*")
            .gte("current_q", 9)
            .limit(500)
            .execute()
        )
        players = eligible.data or []
        if not players:
            raise RuntimeError("아직 추첨 대상(9번 이상 완료)이 없습니다.")

        w = random.choice(players)
        payload = {"winner_name": w.get("name", ""), "age_group": w.get("age_group", "")}
        ins = self.sb.table("quiz_lucky_winners").insert(payload).execute()
        row = (ins.data or [{}])[0]
        return {
            "winner_name": row.get("winner_name", payload["winner_name"]),
            "age_group": row.get("age_group", payload["age_group"]),
            "created_at": str(row.get("created_at", "")),
        }

    def get_winners(self, limit: int = 10) -> List[Dict[str, Any]]:
        res = (
            self.sb.table("quiz_lucky_winners")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = res.data or []
        out = []
        for r in rows:
            out.append(
                {
                    "winner_name": r.get("winner_name", ""),
                    "age_group": r.get("age_group", ""),
                    "created_at": str(r.get("created_at", "")),
                }
            )
        return out


def get_store() -> Tuple[str, Any]:
    """Return (mode, store). mode in {"supabase","memory"}"""
    url = st.secrets.get("supabase_url") if hasattr(st, "secrets") else None
    key = st.secrets.get("supabase_key") if hasattr(st, "secrets") else None

    if url and key:
        try:
            return "supabase", SupabaseStore(url, key)
        except Exception as e:
            st.warning(f"Supabase 연결 실패 → memory로 전환합니다. (사유: {e})")
            return "memory", MemoryStore()

    return "memory", MemoryStore()


# =============================
# UI Helpers
# =============================
def render_leaderboard(store: Any, my_player_id: Optional[str] = None) -> None:
    st.subheader("🏆 리더보드")
    lb = store.get_leaderboard(limit=50)

    if not lb:
        st.info("아직 참가자가 없습니다.")
        return

    rows = []
    my_rank = None
    for i, p in enumerate(lb, start=1):
        rows.append(
            {
                "순위": i,
                "닉네임": p.name,
                "리그": p.age_group,
                "점수": round(p.score, 2),
                "정답수": p.correct_count,
                "총소요(초)": round(p.total_time, 2),
                "진행": f"{p.current_q}/10",
            }
        )
        if my_player_id and p.player_id == my_player_id:
            my_rank = i

    st.dataframe(rows, use_container_width=True, hide_index=True)
    if my_rank:
        st.success(f"내 현재 순위: **{my_rank}위**")


def reset_question_timer(q_index: int) -> None:
    # 문제 인덱스가 바뀔 때만 타이머를 세팅(재렌더링으로 리셋되지 않게)
    if st.session_state.get("timer_q_index") != q_index:
        st.session_state.timer_q_index = q_index
        st.session_state.q_start = time.perf_counter()


def elapsed_time() -> float:
    start = st.session_state.get("q_start")
    if not start:
        return 999.0
    return round(time.perf_counter() - start, 2)


# =============================
# App
# =============================
st.set_page_config(page_title="Paris Quiz (10)", page_icon="🗼", layout="centered")
st.title("🗼 Paris Quiz (10문제)")
mode, store = get_store()
st.caption(f"저장 모드: **{mode}**  |  채점: **0.01초 단위 시간차등**  |  체크포인트: 3/6/9")

with st.sidebar:
    st.header("⚙️ 운영 설정(확장용)")
    st.write("- MZ / 50+ 리그 분리 가능")
    st.write("- 9번 후 럭키드로우 1회")
    st.divider()
    st.write("디버그용(개발 중)")
    st.write("player_id:", st.session_state.get("player_id"))
    st.write("q_index:", st.session_state.get("q_index"))
    st.write("score:", st.session_state.get("score"))


# -----------------------------
# Session init
# -----------------------------
if "started" not in st.session_state:
    st.session_state.started = False
if "player_id" not in st.session_state:
    st.session_state.player_id = None
if "q_index" not in st.session_state:
    st.session_state.q_index = 0
if "score" not in st.session_state:
    st.session_state.score = 0.0
if "correct_count" not in st.session_state:
    st.session_state.correct_count = 0
if "total_time" not in st.session_state:
    st.session_state.total_time = 0.0
if "last_feedback" not in st.session_state:
    st.session_state.last_feedback = None
if "await_next" not in st.session_state:
    st.session_state.await_next = False


# -----------------------------
# Start screen / Registration
# -----------------------------
if not st.session_state.started:
    st.subheader("🎬 인트로(2~3분) 후 바로 시작 가능")
    st.write(
        "10문제(파리) / 총 10~15분 운영을 목표로 설계했습니다.\n\n"
        "- 1초 미만 정답: 최대점수\n"
        "- 10초 이상: 0점\n"
        "- 3/6/9번 문제 후 전체 순위 공개\n"
        "- 9번 문제 후 럭키드로우(추첨)로 이탈 방지"
    )

    with st.form("register_form", clear_on_submit=False):
        nickname = st.text_input("닉네임", max_chars=12, placeholder="예: 행자, 회장님, ParisKing...")
        age_group = st.selectbox("리그(확장 가능)", ["MZ", "50+", "ALL(통합)"], index=2)
        start_btn = st.form_submit_button("🚀 퀴즈 시작")

    if start_btn:
        if not nickname.strip():
            st.error("닉네임을 입력해주세요.")
            st.stop()

        pid = str(uuid.uuid4())
        st.session_state.player_id = pid
        st.session_state.nickname = nickname.strip()
        st.session_state.age_group = age_group
        st.session_state.started = True
        st.session_state.q_index = 0
        st.session_state.score = 0.0
        st.session_state.correct_count = 0
        st.session_state.total_time = 0.0
        st.session_state.await_next = False
        st.session_state.last_feedback = None

        # ✅ 참가자 등록 즉시 row 생성(핵심)
        try:
            store.init_player(
                Player(
                    player_id=pid,
                    name=st.session_state.nickname,
                    age_group=st.session_state.age_group,
                    score=0.0,
                    correct_count=0,
                    total_time=0.0,
                    current_q=0,
                )
            )
            st.success("참가자 등록 완료 ✅")
        except Exception as e:
            st.error(f"참가자 저장 실패 ❌ (Supabase/RLS/키 확인 필요): {e}")
            st.stop()

        st.rerun()

    st.stop()


# -----------------------------
# Guard: must have player_id
# -----------------------------
pid = st.session_state.get("player_id")
if not pid:
    st.warning("세션이 초기화되었습니다. 다시 참가자 등록을 해주세요.")
    st.session_state.started = False
    st.rerun()


# -----------------------------
# Quiz flow
# -----------------------------
q_index = st.session_state.q_index

# Finish
if q_index >= len(QUESTIONS):
    st.balloons()
    st.header("🎉 종료!")
    st.write(f"최종 점수: **{round(st.session_state.score, 2)}점**")
    st.write(f"정답 수: **{st.session_state.correct_count}/10**")
    st.write(f"총 소요 시간: **{round(st.session_state.total_time, 2)}초**")

    st.divider()
    render_leaderboard(store, my_player_id=pid)

    st.subheader("🎁 최근 럭키드로우 당첨자")
    try:
        winners = store.get_winners(limit=5)
        if winners:
            st.dataframe(winners, use_container_width=True, hide_index=True)
        else:
            st.info("아직 당첨자가 없습니다.")
    except Exception as e:
        st.warning(f"당첨자 조회 실패: {e}")

    if st.button("🔁 다시하기(내 세션만)"):
        # 새 플레이어로 새 세션
        for k in ["started", "player_id", "q_index", "score", "correct_count", "total_time", "last_feedback", "await_next"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

    st.stop()


# Current question
q = QUESTIONS[q_index]
q_no = q_index + 1

st.progress(q_no / 10.0, text=f"진행: {q_no}/10")
st.subheader(f"Q{q_no}. (난이도 {q['difficulty']})")

if q.get("type") == "image" and q.get("image_url"):
    st.image(q["image_url"], caption="이미지 문제", use_container_width=True)

st.write(q["question"])

reset_question_timer(q_index)

# If we are in "feedback" state, show feedback and next button
if st.session_state.await_next:
    fb = st.session_state.last_feedback or {}
    if fb.get("correct"):
        st.success(f"정답 ✅ (+{fb.get('gained', 0)}점)  |  소요 {fb.get('elapsed', 0)}초")
    else:
        st.error(f"오답 ❌ (0점)  |  소요 {fb.get('elapsed', 0)}초  |  정답: {fb.get('correct_answer_text')}")

    # 체크포인트(3/6/9): 리더보드 공개
    if q_no in CHECKPOINTS:
        st.divider()
        render_leaderboard(store, my_player_id=pid)

    # 9번 이후 럭키드로우
    if q_no == 9:
        st.divider()
        st.subheader("🎲 럭키드로우(9번 종료 후)")
        if st.button("🎁 추첨 실행(1회)", type="primary"):
            try:
                w = store.lucky_draw()
                st.success(f"당첨자: **{w['winner_name']}**  |  리그: **{w['age_group']}**")
                st.caption(f"기록시간: {w.get('created_at', '')}")
            except Exception as e:
                st.error(f"추첨 실패: {e}")

        try:
            winners = store.get_winners(limit=5)
            if winners:
                st.write("최근 당첨 기록")
                st.dataframe(winners, use_container_width=True, hide_index=True)
        except Exception:
            pass

    if st.button("➡️ 다음 문제", type="primary"):
        st.session_state.await_next = False
        st.session_state.last_feedback = None
        st.session_state.q_index += 1
        st.rerun()

    st.stop()


# Answer form (prevents rerun until submit)
with st.form(f"q_form_{q_no}", clear_on_submit=False):
    choice = st.radio("정답을 선택하세요", q["options"], index=None)
    submitted = st.form_submit_button("✅ 제출")

if submitted:
    if choice is None:
        st.warning("보기 중 하나를 선택한 뒤 제출하세요.")
        st.stop()

    elapsed = elapsed_time()
    is_correct = (q["options"].index(choice) == q["answer"])

    gained = 0.0
    if is_correct:
        mult = time_multiplier(elapsed)
        gained = round(q["base_points"] * mult, 2)

    # Update session totals
    st.session_state.total_time = round(st.session_state.total_time + elapsed, 2)
    if is_correct:
        st.session_state.score = round(st.session_state.score + gained, 2)
        st.session_state.correct_count += 1

    # Persist
    try:
        store.upsert_player(
            Player(
                player_id=pid,
                name=st.session_state.nickname,
                age_group=st.session_state.age_group,
                score=float(st.session_state.score),
                correct_count=int(st.session_state.correct_count),
                total_time=float(st.session_state.total_time),
                current_q=int(q_no),  # 현재까지 완료한 문제 수
            )
        )
    except Exception as e:
        st.error(f"저장 실패 ❌ (RLS/정책/키/테이블명 확인): {e}")
        st.stop()

    # Feedback state
    st.session_state.last_feedback = {
        "correct": is_correct,
        "elapsed": elapsed,
        "gained": gained,
        "correct_answer_text": q["options"][q["answer"]],
    }
    st.session_state.await_next = True
    st.rerun()
