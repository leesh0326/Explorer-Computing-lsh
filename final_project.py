
from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, time as dtime, timedelta
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import urljoin

import folium
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from streamlit_folium import st_folium
import urllib.parse
import streamlit.components.v1 as components

def snu_map_search_url(query: str) -> str:
    """
    공식 서울대 캠퍼스맵을 새 탭에서 열기 위한 URL입니다.
    캠퍼스맵이 검색어 파라미터를 공식 문서로 공개한 것은 아니므로,
    기본 지도 URL을 열고 사용자가 검색할 장소 텍스트를 함께 제공합니다.
    """
    return "https://map.snu.ac.kr/web/main.action"


def official_map_button_html(label: str, query: str) -> str:
    escaped_label = html_escape(label)
    escaped_query = html_escape(query)
    url = snu_map_search_url(query)

    return f"""
    <div style="
        border:1px solid #ddd;
        border-radius:10px;
        padding:12px;
        margin-bottom:8px;
        background:#fafafa;
    ">
      <b>{escaped_label}</b><br>
      <span style="font-size:0.9em;">검색어: {escaped_query}</span><br>
      <a href="{url}" target="_blank">공식 서울대 캠퍼스맵 열기</a>
    </div>
    """

# ============================================================
# 0. 기본 설정
# ============================================================

FOOD_URL = "https://snuco.snu.ac.kr/foodmenu/#none"
SNU_MAP_URL = "https://map.snu.ac.kr/web/main.action#"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    )
}

SNU_CENTER = (37.4593, 126.9515)

SEMINAR_URLS = [
    "https://cse.snu.ac.kr/community/seminar",
    "https://ece.snu.ac.kr/community/events?sc=y",
    "https://me.snu.ac.kr/%ec%84%b8%eb%af%b8%eb%82%98-%eb%b0%8f-%ed%96%89%ec%82%ac/",
    "https://ere.snu.ac.kr/bbs/board.php?bo_table=sub5_1&sca=%EC%84%B8%EB%AF%B8%EB%82%98",
    "https://nucleng.snu.ac.kr/community/seminar",
    "https://medicine.snu.ac.kr/fnt/bbm/sbbs/selectBbsSmpleList.do?bbsId=BBSMSTR_000000000010",
    "https://cbe.snu.ac.kr/%ec%84%b8%eb%af%b8%eb%82%98-%ea%b3%b5%ec%a7%80%ec%82%ac%ed%95%ad/",
    "https://snupharm.snu.ac.kr/%ed%95%99%ec%88%a0%ed%96%89%ec%82%ac-%ec%84%b8%eb%af%b8%eb%82%98-%ec%95%88%eb%82%b4-%eb%b0%8f-%ec%8b%a0%ec%b2%ad/",
    "https://physics.snu.ac.kr/boards/seminar",
    "https://physics.snu.ac.kr/boards/colloquium",
    "https://chem.snu.ac.kr/community/seminar",
    "https://sees.snu.ac.kr/boards/seminar",
    "https://biosci.snu.ac.kr/board/seminars-events",
    "https://stat.snu.ac.kr/category/board-18-SC-D677W0I9-20210304004456/",
    "https://aerospace.snu.ac.kr/board/seminars",
    "https://mse.snu.ac.kr/snumse-main/notice/seminar-colloquium/",
    "https://biomed.snu.ac.kr/en/community/seminar",
    "https://gsds.snu.ac.kr/news/news-seminar/",
]


# ============================================================
# 1. 좌표 데이터
# ============================================================

BUILDING_COORDS: Dict[str, Tuple[float, float]] = {
    "16": (37.4597, 126.9516),
    "25-1": (37.4549, 126.9532),
    "26": (37.4591, 126.9502),
    "28": (37.4548, 126.9537),
    "30-2": (37.4549, 126.9518),
    "38": (37.4572, 126.9502),
    "43-1": (37.4595, 126.9542),
    "56": (37.4571, 126.9529),
    "62": (37.4590, 126.9522),
    "63": (37.4592, 126.9530),
    "65": (37.4582, 126.9538),
    "74": (37.4620, 126.9507),
    "75-1": (37.4614, 126.9500),
    "101": (37.4642, 126.9504),
    "109": (37.4580, 126.9521),
    "113": (37.4574, 126.9494),
    "125": (37.4651, 126.9575),
    "132": (37.4531, 126.9533),
    "133": (37.4524, 126.9530),
    "137-2": (37.4667, 126.9485),
    "200": (37.4593, 126.9483),
    "220": (37.4567, 126.9482),
    "301": (37.4496, 126.9526),
    "302": (37.4489, 126.9520),
    "310": (37.4514, 126.9511),
    "500": (37.4548, 126.9516),
    "501": (37.4543, 126.9509),
    "900": (37.4617, 126.9588),
    "919": (37.4626, 126.9582),
    "944": (37.4602, 126.9606),
    "104-1": (37.4635, 126.9510),
}

BUILDING_LABELS: Dict[str, str] = {
    "16": "사회과학대학",
    "25-1": "자연과학대학 국제회의실",
    "26": "자연과학대학",
    "28": "화학부",
    "30-2": "공간/공대 간이식당 후보",
    "38": "글로벌공학관",
    "43-1": "행정관 인근",
    "56": "자연대 인근",
    "62": "중앙도서관",
    "63": "학생회관",
    "65": "교수회관",
    "74": "예술계복합연구동",
    "75-1": "제3식당/전망대",
    "101": "아시아연구소",
    "109": "자하연",
    "113": "동원관",
    "125": "호암교수회관",
    "132": "뉴미디어통신공동연구소",
    "133": "전기정보공학부 인근",
    "137-2": "언어교육원",
    "200": "농생대 인근",
    "220": "220동",
    "301": "제1공학관",
    "302": "제2공학관",
    "310": "공대 인근",
    "500": "목암홀/자연대",
    "501": "자연과학관",
    "900": "생활관",
    "919": "관악사",
    "944": "삼성전자서울대공동연구소",
}

PLACE_ALIASES: Dict[str, str] = {
    # 자주 쓰는 건물명
    "학생회관": "63",
    "학관": "63",
    "중앙도서관": "62",
    "중도": "62",
    "자하연": "109",
    "농협": "109",
    "동원관": "113",
    "제1공학관": "301",
    "신공학관": "301",
    "301동 식당": "301",
    "301동식당": "301",
    "제2공학관": "302",
    "302동 식당": "302",
    "302동식당": "302",
    "소프트웨어실습실": "302",
    "전망대": "75-1",
    "제3식당": "75-1",
    "3식당": "75-1",
    "두레미담": "75-1",
    "예술계복합연구동": "74",
    "예술계식당": "74",
    "아름드리": "74",
    "기숙사": "919",
    "관악사": "919",
    "기숙사식당": "919",
    "생활관": "900",
    "생활관식당": "900",
    "공간": "30-2",
    "공대간이식당": "30-2",
    "공대 간이식당": "30-2",
    "화학부": "28",
    "자연과학관": "501",
    "목암홀": "500",
    "뉴미디어통신공동연구소": "132",
    "반도체공동연구소": "104-1",
    "삼성전자서울대공동연구소": "944",
}

PLACE_KEYWORDS: Dict[str, Tuple[str, float, float]] = {
    "중앙도서관": ("62", BUILDING_COORDS["62"][0], BUILDING_COORDS["62"][1]),
    "양두석홀": ("62", BUILDING_COORDS["62"][0], BUILDING_COORDS["62"][1]),
    "목암홀": ("500", BUILDING_COORDS["500"][0], BUILDING_COORDS["500"][1]),
    "뉴미디어통신": ("132", BUILDING_COORDS["132"][0], BUILDING_COORDS["132"][1]),
    "삼성전자서울대공동연구소": ("944", BUILDING_COORDS["944"][0], BUILDING_COORDS["944"][1]),
    "소프트웨어실습실": ("302", BUILDING_COORDS["302"][0], BUILDING_COORDS["302"][1]),
}


# ============================================================
# 2. 식당 데이터
# ============================================================

@dataclass
class Restaurant:
    display_name: str
    aliases: List[str]
    building_no: str
    place: str
    lat: float
    lon: float


@dataclass
class Meal:
    restaurant: str
    meal_type: str
    menu: str
    price: str
    operating_time: str


RESTAURANTS: List[Restaurant] = [
    Restaurant(
        "공대간이식당",
        ["공대간이식당", "공대 간이식당", "공간", "공대간이"],
        "30-2",
        "30-2동 1층",
        *BUILDING_COORDS["30-2"],
    ),
    Restaurant(
        "301동 식당",
        ["301동 식당", "301동식당", "제1공학관식당", "제 1공학관식당", "1공학관식당"],
        "301",
        "제1공학관(301동) 지하1층/1층",
        *BUILDING_COORDS["301"],
    ),
    Restaurant(
        "302동 식당",
        ["302동 식당", "302동식당", "제2공학관식당", "제 2공학관식당", "2공학관식당"],
        "302",
        "제2공학관(302동) 1층",
        *BUILDING_COORDS["302"],
    ),
    Restaurant(
        "3식당",
        ["3식당", "제3식당", "제 3식당", "전망대식당"],
        "75-1",
        "전망대(75-1동) 3층",
        *BUILDING_COORDS["75-1"],
    ),
    Restaurant(
        "기숙사식당",
        ["기숙사식당", "기숙사 식당", "관악사식당"],
        "919",
        "관악사(919동) 1층",
        *BUILDING_COORDS["919"],
    ),
    Restaurant(
        "동원관식당",
        ["동원관식당", "동원관 식당"],
        "113",
        "113동 2층",
        *BUILDING_COORDS["113"],
    ),
    Restaurant(
        "두레미담",
        ["두레미담"],
        "75-1",
        "전망대(75-1동) 5층",
        *BUILDING_COORDS["75-1"],
    ),
    Restaurant(
        "예술계식당",
        ["예술계식당", "예술계 식당", "예술계 아름드리 식당", "아름드리 식당"],
        "74",
        "예술계복합연구동(74동) 지하 1층",
        *BUILDING_COORDS["74"],
    ),
    Restaurant(
        "자하연식당 2층",
        ["자하연식당 2층", "자하연식당", "자하연 2층", "자하연"],
        "109",
        "농협(109동) 2층",
        *BUILDING_COORDS["109"],
    ),
    Restaurant(
        "자하연식당 3층",
        ["자하연식당 3층", "자하연 3층", "자하연"],
        "109",
        "농협(109동) 3층",
        *BUILDING_COORDS["109"],
    ),
    Restaurant(
        "학생회관 식당",
        ["학생회관 식당", "학생회관식당", "학관식당", "학관"],
        "63",
        "학생회관(63동) 1층",
        *BUILDING_COORDS["63"],
    ),
]

RESTAURANT_NAMES = [r.display_name for r in RESTAURANTS]


# ============================================================
# 3. 행사 데이터 구조
# ============================================================

@dataclass
class SeminarEvent:
    title: str
    start_dt: datetime
    end_dt: Optional[datetime]
    place: str
    source_name: str
    source_url: str
    building_no: Optional[str]
    lat: Optional[float]
    lon: Optional[float]


# ============================================================
# 4. 공통 유틸리티
# ============================================================

def render_restaurant_cards(restaurants: Sequence[str], meals: Sequence[Meal]) -> None:
    meal_type, menu_date = current_meal_slot()

    st.subheader("식당 + 메뉴")
    st.caption(f"현재 식단 기준: {menu_date.strftime('%Y.%m.%d')} {meal_type}")

    restaurant_lookup = {r.display_name: r for r in RESTAURANTS}

    for name in restaurants:
        restaurant = restaurant_lookup.get(name)
        meal = pick_meal(name, meals, meal_type)

        if not restaurant:
            continue

        with st.container(border=True):
            st.markdown(f"### 🍽️ {restaurant.display_name}")
            st.write(f"**위치:** {restaurant.place}")

            if meal:
                st.write(f"**메뉴:** {meal.menu or '-'}")
                st.write(f"**가격:** {meal.price or '-'}")
                st.write(f"**운영시간:** {meal.operating_time or '-'}")
            else:
                st.write("현재 시간대 메뉴를 찾지 못했습니다.")

            st.link_button(
                "공식 캠퍼스맵에서 위치 확인",
                snu_map_search_url(restaurant.place),
            )

def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize(value: str) -> str:
    return re.sub(r"[\s()\-.·_/]", "", value).lower()


def html_escape(value: object) -> str:
    text = str(value or "")
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def fetch_soup(url: str, timeout: int = 12) -> BeautifulSoup:
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return BeautifulSoup(response.text, "html.parser")


def parse_building_no(place: str) -> Optional[str]:
    patterns = [
        r"(\d{1,3}(?:-\d+)?)\s*동",
        r"Building\s*(\d{1,3}(?:-\d+)?)",
        r"building\s*(\d{1,3}(?:-\d+)?)",
        r"\bBldg\.?\s*(\d{1,3}(?:-\d+)?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, place, flags=re.I)
        if match:
            return match.group(1)

    return None

def resolve_building_no(place: str) -> Optional[str]:
    """
    장소 문자열에서 실제 지도 좌표를 찾기 위한 건물번호를 반환합니다.

    예:
    - "302동 309-1호" -> "302"
    - "제2공학관 309호" -> "302"
    - "공간" -> "30-2"
    - "자하연식당 3층" -> "109"
    """
    place = clean_text(place)

    # 1. "302동", "75-1동"처럼 동번호가 직접 들어 있으면 우선 사용
    building_no = parse_building_no(place)

    if building_no and building_no in BUILDING_COORDS:
        return building_no

    # 2. 동번호가 없거나 좌표표에 없는 경우, 별칭으로 찾기
    place_n = normalize(place)

    # 긴 별칭부터 검사해야 "301동 식당" 같은 표현이 안정적으로 잡힙니다.
    for alias, mapped_no in sorted(PLACE_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        alias_n = normalize(alias)

        if alias_n and alias_n in place_n:
            return mapped_no

    return building_no

def coords_for_place(place: str) -> Tuple[Optional[str], Optional[float], Optional[float]]:
    building_no = resolve_building_no(place)

    if building_no and building_no in BUILDING_COORDS:
        lat, lon = BUILDING_COORDS[building_no]
        return building_no, lat, lon

    for keyword, value in PLACE_KEYWORDS.items():
        if keyword.lower() in place.lower():
            return value

    return building_no, None, None


def format_dt(dt: datetime) -> str:
    return dt.strftime("%Y.%m.%d %H:%M")


def format_event_time(start_dt: datetime, end_dt: Optional[datetime]) -> str:
    if end_dt:
        return f"{format_dt(start_dt)} ~ {end_dt.strftime('%H:%M')}"
    return format_dt(start_dt)


# ============================================================
# 5. 시간표 입력 처리
# ============================================================

def parse_schedule_entries() -> List[dict]:
    entries = []

    for i in range(10):
        course = clean_text(st.session_state.get(f"course_{i}", ""))
        time_text = clean_text(st.session_state.get(f"class_time_{i}", ""))
        place = clean_text(st.session_state.get(f"class_place_{i}", ""))

        if not course and not time_text and not place:
            continue

        building_no = resolve_building_no(place)
        lat = lon = None

        if building_no and building_no in BUILDING_COORDS:
            lat, lon = BUILDING_COORDS[building_no]

        entries.append(
            {
                "index": i + 1,
                "course": course or f"강의 {i + 1}",
                "time": time_text,
                "place": place,
                "building_no": building_no,
                "lat": lat,
                "lon": lon,
            }
        )

    return entries


# ============================================================
# 6. 식단 크롤링
# ============================================================

def current_meal_slot(now: Optional[datetime] = None) -> Tuple[str, date]:
    """
    사용자 요구사항:
    - 전날 20:00 ~ 다음날 10:00: 아침
    - 10:00 ~ 14:30: 점심
    - 14:30 ~ 20:00: 저녁

    20:00 이후에는 다음날 아침 식단을 보는 것으로 처리합니다.
    """
    now = now or datetime.now()
    t = now.time()

    if t >= dtime(20, 0):
        return "아침", now.date() + timedelta(days=1)

    if t < dtime(10, 0):
        return "아침", now.date()

    if t < dtime(14, 30):
        return "점심", now.date()

    return "저녁", now.date()


def match_restaurant_name(text: str) -> Optional[str]:
    text_n = normalize(text)

    for restaurant in RESTAURANTS:
        for alias in restaurant.aliases:
            alias_n = normalize(alias)
            if alias_n and (alias_n in text_n or text_n in alias_n):
                return restaurant.display_name

    return None


def extract_price(text: str) -> str:
    prices = re.findall(r"\d{1,3}(?:,\d{3})*\s*원", text)
    return ", ".join(dict.fromkeys([p.replace(" ", "") for p in prices]))


def extract_operating_time(text: str) -> str:
    match = re.search(r"\d{1,2}:\d{2}\s*[~\-]\s*\d{1,2}:\d{2}", text)
    return match.group(0).replace(" ", "") if match else ""


def clean_menu_text(text: str) -> str:
    text = re.sub(r"※\s*운영시간\s*[:：]?\s*\d{1,2}:\d{2}\s*[~\-]\s*\d{1,2}:\d{2}", "", text)
    text = re.sub(r"\d{1,3}(?:,\d{3})*\s*원", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" /,.-")


def parse_food_tables(html: str) -> List[Meal]:
    meals: List[Meal] = []

    try:
        tables = pd.read_html(html)
    except Exception:
        return meals

    for df in tables:
        if df.empty:
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [" ".join([clean_text(x) for x in col if clean_text(x)]) for col in df.columns]
        else:
            df.columns = [clean_text(c) for c in df.columns]

        name_col = next((c for c in df.columns if "식당" in clean_text(c)), df.columns[0])
        meal_cols = {
            "아침": next((c for c in df.columns if "아침" in clean_text(c)), None),
            "점심": next((c for c in df.columns if "점심" in clean_text(c)), None),
            "저녁": next((c for c in df.columns if "저녁" in clean_text(c)), None),
        }

        if not any(meal_cols.values()):
            continue

        for _, row in df.iterrows():
            raw_name = clean_text(row.get(name_col, ""))
            matched_name = match_restaurant_name(raw_name)

            if not matched_name:
                continue

            for meal_type, col in meal_cols.items():
                if col is None:
                    continue

                raw_menu = clean_text(row.get(col, ""))

                if not raw_menu or raw_menu.lower() == "nan" or raw_menu in ["-", "휴무"]:
                    continue

                meals.append(
                    Meal(
                        restaurant=matched_name,
                        meal_type=meal_type,
                        menu=clean_menu_text(raw_menu),
                        price=extract_price(raw_menu),
                        operating_time=extract_operating_time(raw_menu),
                    )
                )

    return meals


def parse_food_text(text: str) -> List[Meal]:
    """
    테이블 파싱이 실패할 때 사용하는 보조 파서입니다.
    SNUCO 페이지의 텍스트에서 식당명 블록을 찾고, 가격이 포함된 메뉴를 추출합니다.
    """
    text = "\n".join([clean_text(line) for line in text.splitlines() if clean_text(line)])
    positions = []

    for restaurant in RESTAURANTS:
        for alias in restaurant.aliases:
            pos = text.find(alias)
            if pos != -1:
                positions.append((pos, restaurant.display_name))
                break

    positions = sorted(set(positions))
    meals: List[Meal] = []

    for idx, (pos, restaurant_name) in enumerate(positions):
        end = positions[idx + 1][0] if idx + 1 < len(positions) else min(len(text), pos + 900)
        block = text[pos:end]
        chunks = re.split(r"(?=\S.{0,80}\s*:\s*\d{1,3}(?:,\d{3})*\s*원)", block)
        meal_order = ["아침", "점심", "저녁"]
        meal_idx = 0

        for chunk in chunks:
            chunk = clean_text(chunk)

            if "원" not in chunk:
                continue

            meal_type = meal_order[min(meal_idx, 2)]
            meal_idx += 1

            meals.append(
                Meal(
                    restaurant=restaurant_name,
                    meal_type=meal_type,
                    menu=clean_menu_text(chunk),
                    price=extract_price(chunk),
                    operating_time=extract_operating_time(chunk),
                )
            )

    return meals


@st.cache_data(ttl=30 * 60)
def crawl_food_menus_cached(meal_type: str, menu_date: str) -> List[dict]:
    """
    생협 식단 페이지를 BeautifulSoup으로 가져오고, pandas/정규식으로 식당별 메뉴를 파싱합니다.
    menu_date는 캐시 키로 사용됩니다. SNUCO 페이지가 날짜 파라미터를 공식적으로
    공개하지 않으므로, 실제 요청은 기본 페이지에 수행합니다.
    """
    try:
        response = requests.get(FOOD_URL, headers=HEADERS, timeout=12)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return []

    meals = parse_food_tables(html)

    if not meals:
        meals = parse_food_text(soup.get_text("\n"))

    unique: Dict[Tuple[str, str, str], Meal] = {}

    for meal in meals:
        key = (meal.restaurant, meal.meal_type, meal.menu[:50])
        unique[key] = meal

    return [m.__dict__ for m in unique.values()]


def pick_meal(restaurant_name: str, meals: Sequence[Meal], meal_type: str) -> Optional[Meal]:
    candidates = [m for m in meals if normalize(m.restaurant) == normalize(restaurant_name)]

    if not candidates:
        candidates = [
            m for m in meals
            if normalize(m.restaurant) in normalize(restaurant_name)
            or normalize(restaurant_name) in normalize(m.restaurant)
        ]

    for meal in candidates:
        if meal.meal_type == meal_type:
            return meal

    return candidates[0] if candidates else None


# ============================================================
# 7. Selenium 행사/세미나 크롤링
# ============================================================

MONTHS_EN = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


def parse_date_candidates(text: str, now: Optional[datetime] = None) -> List[date]:
    now = now or datetime.now()
    candidates: List[date] = []

    # 2026/6/11, 2026-06-11, 2026. 06. 11, 2026년 6월 11일
    for y, m, d in re.findall(
        r"(20\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})",
        text,
    ):
        try:
            candidates.append(date(int(y), int(m), int(d)))
        except ValueError:
            pass

    # June 8, 2026
    for month_name, d, y in re.findall(
        r"\b([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(20\d{2})\b",
        text,
    ):
        month = MONTHS_EN.get(month_name.lower())
        if month:
            try:
                candidates.append(date(int(y), month, int(d)))
            except ValueError:
                pass

    # 20 Feb, 2026
    for d, month_name, y in re.findall(
        r"\b(\d{1,2})\s+([A-Za-z]{3,9}),?\s+(20\d{2})\b",
        text,
    ):
        month = MONTHS_EN.get(month_name.lower())
        if month:
            try:
                candidates.append(date(int(y), month, int(d)))
            except ValueError:
                pass

    # 6월 11일처럼 연도 없는 경우
    for m, d in re.findall(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", text):
        try:
            parsed = date(now.year, int(m), int(d))
            if parsed < now.date() - timedelta(days=30):
                parsed = date(now.year + 1, int(m), int(d))
            candidates.append(parsed)
        except ValueError:
            pass

    unique: List[date] = []
    seen = set()

    for item in candidates:
        if item not in seen:
            unique.append(item)
            seen.add(item)

    return unique

def parse_time_candidates(text: str) -> Tuple[dtime, Optional[dtime]]:
    # 17:00 ~ 18:00
    match = re.search(r"(\d{1,2}):(\d{2})\s*[~\-]\s*(\d{1,2}):(\d{2})", text)

    if match:
        h1, m1, h2, m2 = map(int, match.groups())
        if 0 <= h1 <= 23 and 0 <= h2 <= 23 and 0 <= m1 <= 59 and 0 <= m2 <= 59:
            return dtime(h1, m1), dtime(h2, m2)

    # PM 02:00 / AM 10:00
    match = re.search(r"\b(AM|PM)\s*(\d{1,2}):(\d{2})\b", text, flags=re.I)

    if match:
        meridiem, h, m = match.groups()
        h, m = int(h), int(m)

        if meridiem.upper() == "PM" and h != 12:
            h += 12
        if meridiem.upper() == "AM" and h == 12:
            h = 0

        if 0 <= h <= 23 and 0 <= m <= 59:
            return dtime(h, m), None

    # 오후 2시 / 오전 10시 30분
    match = re.search(r"(오전|오후)\s*(\d{1,2})\s*시(?:\s*(\d{1,2})\s*분)?", text)

    if match:
        meridiem, h, m = match.groups()
        h = int(h)
        m = int(m or 0)

        if meridiem == "오후" and h != 12:
            h += 12
        if meridiem == "오전" and h == 12:
            h = 0

        return dtime(h, m), None

    return dtime(0, 0), None


def extract_place(text: str) -> str:
    lines = [clean_text(line) for line in text.splitlines() if clean_text(line)]

    for line in lines:
        match = re.search(
            r"(장소|Place|Location|Venue|Where)\s*[:：]\s*(.+)",
            line,
            flags=re.I,
        )
        if match:
            return clean_text(match.group(2))

    for line in lines:
        if len(line) > 180:
            continue

        if re.search(
            r"\d{1,3}(?:-\d+)?\s*동|Building\s*\d{1,3}(?:-\d+)?|Bldg\.?\s*\d{1,3}(?:-\d+)?|Room\s*\d|Rm\.?\s*\d|호",
            line,
            flags=re.I,
        ):
            return line

    known_place_keywords = [
        "소프트웨어실습실",
        "뉴미디어통신",
        "반도체공동연구소",
        "삼성전자서울대공동연구소",
        "목암홀",
        "양두석홀",
        "중앙도서관",
        "자하연",
        "학생회관",
        "제1공학관",
        "제2공학관",
        "신공학관",
        "세미나실",
        "강의실",
        "강당",
        "홀",
        "Zoom",
        "온라인",
    ]

    for line in lines:
        if len(line) <= 180 and any(keyword.lower() in line.lower() for keyword in known_place_keywords):
            return line

    return ""


def title_from_block(block_text: str) -> str:
    lines = [clean_text(x) for x in block_text.splitlines() if clean_text(x)]

    for line in lines:
        if len(line) < 4:
            continue

        if re.search(r"20\d{2}[.\-/년]|\d{1,2}\s*월\s*\d{1,2}\s*일|^\d{1,2}\s+[A-Za-z]{3}", line):
            continue

        if re.search(r"장소|Place|Location|검색|분류|제목|내용|연사|번호", line, flags=re.I):
            continue

        return line[:180]

    return "제목 없음"


def event_from_text(block_text: str, source_name: str, source_url: str, now: datetime) -> Optional[SeminarEvent]:
    dates = parse_date_candidates(block_text, now=now)

    if not dates:
        return None

    future_dates = [d for d in dates if d >= now.date()]

    if not future_dates:
        return None

    event_date = min(future_dates)
    start_t, end_t = parse_time_candidates(block_text)
    start_dt = datetime.combine(event_date, start_t)
    end_dt = datetime.combine(event_date, end_t) if end_t else None

    if end_dt and end_dt < now:
        return None

    if not end_dt and start_t != dtime(0, 0) and start_dt < now:
        return None

    place = extract_place(block_text)
    building_no, lat, lon = coords_for_place(place)
    title = title_from_block(block_text)

    return SeminarEvent(
        title=title,
        start_dt=start_dt,
        end_dt=end_dt,
        place=place,
        source_name=source_name,
        source_url=source_url,
        building_no=building_no,
        lat=lat,
        lon=lon,
    )


def collect_event_blocks_from_soup(soup: BeautifulSoup) -> List[str]:
    blocks: List[str] = []

    selectors = [
        "article", "li", "tr", ".post", ".entry", ".board", ".list", ".item",
        ".elementor-post", ".seminar", ".event",
    ]

    for selector in selectors:
        for tag in soup.select(selector):
            text = clean_text(tag.get_text("\n"))

            if len(text) < 20:
                continue

            if re.search(
                r"20\d{2}|월\s*\d{1,2}\s*일|January|February|March|April|May|June|July|August|September|October|November|December",
                text,
                flags=re.I,
            ):
                blocks.append(text)

    full_text = soup.get_text("\n")
    lines = [clean_text(x) for x in full_text.splitlines() if clean_text(x)]
    buffer: List[str] = []

    for line in lines:
        buffer.append(line)

        if len(buffer) >= 8:
            candidate = "\n".join(buffer[-8:])
            if re.search(r"20\d{2}|월\s*\d{1,2}\s*일", candidate):
                blocks.append(candidate)

    unique = []
    seen = set()

    for block in blocks:
        block = block[:1200]
        key = normalize(block[:200])

        if key and key not in seen:
            unique.append(block)
            seen.add(key)

    return unique


def collect_detail_links(soup: BeautifulSoup, base_url: str, max_links: int = 50) -> List[Tuple[str, str]]:
    links: List[Tuple[str, str]] = []
    seen = set()

    base_host = re.sub(r"^https?://", "", base_url).split("/")[0]

    skip_words = [
        "login", "로그인", "privacy", "개인정보", "sitemap", "contact",
        "facebook", "instagram", "youtube", "twitter",
        "입학", "학사", "장학", "채용", "교수", "연구실", "소개", "오시는 길",
    ]

    likely_url_words = [
        "seminar", "colloquium", "event", "events", "board", "bbs",
        "notice", "community", "view", "article", "post", "wr_id",
        "bo_table", "idx", "seq", "uid", "no", "news",
    ]

    for a in soup.find_all("a", href=True):
        text = clean_text(a.get_text(" "))
        href = clean_text(a.get("href", ""))

        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue

        full_url = urljoin(base_url, href)
        host = re.sub(r"^https?://", "", full_url).split("/")[0]

        if base_host not in host and host not in base_host:
            continue

        candidate = f"{text} {href}".lower()

        if any(word.lower() in candidate for word in skip_words):
            continue

        has_event_word = bool(
            re.search(
                r"seminar|세미나|colloquium|콜로퀴움|event|행사|20\d{2}|\d{1,2}\s*월",
                candidate,
                flags=re.I,
            )
        )

        has_likely_url = any(word in candidate for word in likely_url_words)

        if not has_event_word and not has_likely_url:
            continue

        if full_url in seen:
            continue

        links.append((text or "상세 페이지", full_url))
        seen.add(full_url)

        if len(links) >= max_links:
            break

    return links


def site_name_from_url(url: str) -> str:
    host = re.sub(r"^https?://", "", url).split("/")[0]
    return host.replace("www.", "")


@st.cache_data(ttl=60 * 60)
@st.cache_data(ttl=60 * 60)
def crawl_events_with_selenium_cached(now_key: str, max_links_per_site: int = 50) -> List[dict]:
    """
    여러 학과 세미나/행사 페이지를 Selenium으로 열고,
    목록 페이지와 상세 페이지에서 현재 이후 행사만 추출합니다.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except Exception:
        return []

    try:
        import chromedriver_autoinstaller
        chromedriver_autoinstaller.install()
    except Exception:
        pass

    now = datetime.now()
    events: List[SeminarEvent] = []

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1600,2200")
    options.add_argument(f"user-agent={HEADERS['User-Agent']}")

    driver = None

    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(25)

        for url in SEMINAR_URLS:
            source_name = site_name_from_url(url)

            try:
                driver.get(url)
                driver.implicitly_wait(5)
                time.sleep(1.5)

                soup = BeautifulSoup(driver.page_source, "html.parser")

                # 목록 페이지에서 바로 추출
                for block in collect_event_blocks_from_soup(soup):
                    event = event_from_text(block, source_name, url, now)
                    if event:
                        events.append(event)

                # 상세 페이지를 더 많이 방문
                detail_links = collect_detail_links(
                    soup,
                    url,
                    max_links=max_links_per_site,
                )

                for title_hint, detail_url in detail_links:
                    try:
                        driver.get(detail_url)
                        driver.implicitly_wait(3)
                        time.sleep(0.7)

                        detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                        text = detail_soup.get_text("\n")

                        event = event_from_text(text, source_name, detail_url, now)

                        if event:
                            if event.title == "제목 없음" and title_hint:
                                event.title = title_hint[:180]

                            events.append(event)

                    except Exception:
                        continue

            except Exception:
                continue

    except Exception:
        return []

    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

    unique: Dict[Tuple[str, str, str, str], SeminarEvent] = {}

    for event in events:
        key = (
            normalize(event.title)[:100],
            event.start_dt.isoformat(),
            normalize(event.place)[:100],
            event.source_name,
        )
        unique[key] = event

    sorted_events = sorted(unique.values(), key=lambda x: x.start_dt)

    return [
        {
            "title": e.title,
            "start_dt": e.start_dt.isoformat(),
            "end_dt": e.end_dt.isoformat() if e.end_dt else None,
            "place": e.place,
            "source_name": e.source_name,
            "source_url": e.source_url,
            "building_no": e.building_no,
            "lat": e.lat,
            "lon": e.lon,
        }
        for e in sorted_events
    ]


def restore_events(raw_events: Sequence[dict]) -> List[SeminarEvent]:
    events = []

    for item in raw_events:
        events.append(
            SeminarEvent(
                title=item["title"],
                start_dt=datetime.fromisoformat(item["start_dt"]),
                end_dt=datetime.fromisoformat(item["end_dt"]) if item.get("end_dt") else None,
                place=item.get("place", ""),
                source_name=item.get("source_name", ""),
                source_url=item.get("source_url", ""),
                building_no=item.get("building_no"),
                lat=item.get("lat"),
                lon=item.get("lon"),
            )
        )

    return events


# ============================================================
# 8. 건물 길찾기
# ============================================================

# WAYPOINTS: Dict[str, Tuple[float, float]] = {
#     "정문": (37.4661, 126.9486),
#     "행정관": (37.4597, 126.9524),
#     "학생회관앞": (37.4591, 126.9531),
#     "중앙도서관앞": (37.4590, 126.9520),
#     "자하연앞": (37.4580, 126.9521),
#     "농생대앞": (37.4591, 126.9482),
#     "자연대앞": (37.4550, 126.9509),
#     "공대삼거리": (37.4520, 126.9517),
#     "제1공학관앞": (37.4497, 126.9527),
#     "제2공학관앞": (37.4489, 126.9521),
#     "기숙사삼거리": (37.4613, 126.9565),
#     "관악사앞": (37.4623, 126.9583),
# }

# BASE_EDGES = [
#     ("정문", "행정관"),
#     ("행정관", "학생회관앞"),
#     ("학생회관앞", "중앙도서관앞"),
#     ("중앙도서관앞", "자하연앞"),
#     ("자하연앞", "자연대앞"),
#     ("자연대앞", "공대삼거리"),
#     ("공대삼거리", "제1공학관앞"),
#     ("제1공학관앞", "제2공학관앞"),
#     ("학생회관앞", "기숙사삼거리"),
#     ("기숙사삼거리", "관악사앞"),
#     ("행정관", "농생대앞"),
#     ("농생대앞", "자연대앞"),
# ]


# def haversine_m(a: Tuple[float, float], b: Tuple[float, float]) -> float:
#     r = 6371000
#     lat1, lon1 = math.radians(a[0]), math.radians(a[1])
#     lat2, lon2 = math.radians(b[0]), math.radians(b[1])
#     dlat = lat2 - lat1
#     dlon = lon2 - lon1
#     h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
#     return 2 * r * math.asin(math.sqrt(h))


# def build_route_graph() -> Dict[str, Dict[str, float]]:
#     coords = {**WAYPOINTS}
#     coords.update({f"{no}동": coord for no, coord in BUILDING_COORDS.items()})

#     graph: Dict[str, Dict[str, float]] = {node: {} for node in coords}

#     def add_edge(a: str, b: str) -> None:
#         dist = haversine_m(coords[a], coords[b])
#         graph[a][b] = dist
#         graph[b][a] = dist

#     for a, b in BASE_EDGES:
#         add_edge(a, b)

#     waypoint_names = list(WAYPOINTS.keys())

#     for building_no, coord in BUILDING_COORDS.items():
#         b_node = f"{building_no}동"
#         nearest = sorted(
#             waypoint_names,
#             key=lambda w: haversine_m(coord, WAYPOINTS[w]),
#         )[:2]

#         for w in nearest:
#             add_edge(b_node, w)

    # return graph


# def dijkstra_path(start: str, end: str) -> Tuple[List[str], float]:
#     graph = build_route_graph()

#     if start not in graph or end not in graph:
#         return [], 0.0

#     unvisited = set(graph.keys())
#     dist = {node: float("inf") for node in graph}
#     prev: Dict[str, Optional[str]] = {node: None for node in graph}
#     dist[start] = 0.0

#     while unvisited:
#         current = min(unvisited, key=lambda node: dist[node])

#         if current == end or dist[current] == float("inf"):
#             break

#         unvisited.remove(current)

#         for neighbor, weight in graph[current].items():
#             if neighbor not in unvisited:
#                 continue

#             alt = dist[current] + weight

#             if alt < dist[neighbor]:
#                 dist[neighbor] = alt
#                 prev[neighbor] = current

#     if dist[end] == float("inf"):
#         return [], 0.0

#     path = []
#     node: Optional[str] = end

#     while node:
#         path.append(node)
#         node = prev[node]

#     path.reverse()
#     return path, dist[end]


# def node_coord(node: str) -> Optional[Tuple[float, float]]:
#     if node in WAYPOINTS:
#         return WAYPOINTS[node]

#     building_no = node.replace("동", "")
#     return BUILDING_COORDS.get(building_no)


# def building_options() -> List[str]:
#     options = []
#     for no in sorted(BUILDING_COORDS.keys(), key=lambda x: (len(x), x)):
#         label = BUILDING_LABELS.get(no, "")
#         options.append(f"{no}동" + (f" - {label}" if label else ""))
#     return options


# def option_to_building_no(option: str) -> Optional[str]:
#     match = re.match(r"(\d{1,3}(?:-\d+)?)동", option)
#     return match.group(1) if match else None


# ============================================================
# 9. 지도 생성
# ============================================================

def restaurant_popup_html(restaurant: Restaurant, meal: Optional[Meal], meal_type: str, menu_date: date) -> str:
    if meal:
        meal_html = f"""
        <b>{html_escape(menu_date.strftime('%Y.%m.%d'))} {html_escape(meal_type)} 식단</b><br>
        메뉴: {html_escape(meal.menu or '-')}<br>
        가격: {html_escape(meal.price or '-')}<br>
        운영시간: {html_escape(meal.operating_time or '-')}
        """
    else:
        meal_html = f"""
        <b>{html_escape(menu_date.strftime('%Y.%m.%d'))} {html_escape(meal_type)} 식단</b><br>
        해당 식당의 현재 시간대 메뉴를 찾지 못했습니다.
        """

    return f"""
    <div style="width:300px">
      <h4 style="margin-bottom:6px">{html_escape(restaurant.display_name)}</h4>
      위치: {html_escape(restaurant.place)}<br>
      데이터 위치 기준: SNU Campus Map<br>
      <hr>
      {meal_html}
    </div>
    """


def event_popup_html(event: SeminarEvent) -> str:
    link = ""

    if event.source_url:
        link = f"<br><a href='{html_escape(event.source_url)}' target='_blank'>원문 보기</a>"

    return f"""
    <div style="width:320px">
      <h4 style="margin-bottom:6px">{html_escape(event.title)}</h4>
      일시: {html_escape(format_event_time(event.start_dt, event.end_dt))}<br>
      장소: {html_escape(event.place or '장소 정보 없음')}<br>
      출처: {html_escape(event.source_name)}
      {link}
    </div>
    """


def schedule_popup_html(entry: dict) -> str:
    return f"""
    <div style="width:260px">
      <h4>{html_escape(entry['course'])}</h4>
      시간: {html_escape(entry['time'])}<br>
      장소: {html_escape(entry['place'])}
    </div>
    """


def make_campus_map(
    selected_restaurant_names: Sequence[str],
    show_food: bool,
    show_events: bool,
    meals: Sequence[Meal],
    events: Sequence[SeminarEvent],
    schedule_entries: Sequence[dict],
    route_start_no: Optional[str],
    route_end_no: Optional[str],
    show_all_buildings: bool = True,
) -> folium.Map:
    m = folium.Map(location=SNU_CENTER, zoom_start=15, control_scale=True, tiles="OpenStreetMap")
    meal_type, menu_date = current_meal_slot()

    if show_all_buildings:
        building_group = folium.FeatureGroup(name="건물 지표", show=True)

        for building_no, coord in BUILDING_COORDS.items():
            label = BUILDING_LABELS.get(building_no, "")
            tooltip = f"{building_no}동" + (f" - {label}" if label else "")

            folium.CircleMarker(
                location=coord,
                radius=4,
                tooltip=tooltip,
                popup=folium.Popup(f"<b>{html_escape(tooltip)}</b>", max_width=240),
                fill=True,
                opacity=0.75,
                fill_opacity=0.75,
            ).add_to(building_group)

        building_group.add_to(m)

    if schedule_entries:
        schedule_group = folium.FeatureGroup(name="내 시간표", show=True)

        for entry in schedule_entries:
            if entry.get("lat") is None or entry.get("lon") is None:
                continue

            folium.Marker(
                location=(entry["lat"], entry["lon"]),
                tooltip=f"{entry['course']} | {entry['place']}",
                popup=folium.Popup(schedule_popup_html(entry), max_width=300),
                icon=folium.Icon(color="orange", icon="book", prefix="fa"),
            ).add_to(schedule_group)

        schedule_group.add_to(m)

    if show_food:
        food_group = folium.FeatureGroup(name="식당 + 메뉴", show=True)
        restaurant_lookup = {r.display_name: r for r in RESTAURANTS}

        for name in selected_restaurant_names:
            restaurant = restaurant_lookup.get(name)

            if not restaurant:
                continue

            meal = pick_meal(name, meals, meal_type)
            tooltip = f"{name} | {meal_type}: {meal.menu[:60] if meal else '메뉴 정보 없음'}"

            folium.Marker(
                location=(restaurant.lat, restaurant.lon),
                tooltip=folium.Tooltip(tooltip, sticky=True),
                popup=folium.Popup(restaurant_popup_html(restaurant, meal, meal_type, menu_date), max_width=340),
                icon=folium.Icon(color="green", icon="cutlery", prefix="fa"),
            ).add_to(food_group)

        food_group.add_to(m)

    if show_events:
        event_group = folium.FeatureGroup(name="행사/세미나", show=True)

        for event in events:
            if event.lat is None or event.lon is None:
                continue

            folium.Marker(
                location=(event.lat, event.lon),
                tooltip=folium.Tooltip(f"{event.title} | {format_event_time(event.start_dt, event.end_dt)}", sticky=True),
                popup=folium.Popup(event_popup_html(event), max_width=360),
                icon=folium.Icon(color="purple", icon="calendar", prefix="fa"),
            ).add_to(event_group)

        event_group.add_to(m)

    if route_start_no and route_end_no and route_start_no != route_end_no:
        start_node = f"{route_start_no}동"
        end_node = f"{route_end_no}동"
        path, distance_m = dijkstra_path(start_node, end_node)
        coords = [node_coord(node) for node in path]
        coords = [coord for coord in coords if coord is not None]

        if len(coords) >= 2:
            folium.PolyLine(
                locations=coords,
                weight=6,
                opacity=0.85,
                tooltip=f"{start_node} → {end_node} | 약 {distance_m:.0f}m",
            ).add_to(m)

            folium.Marker(
                coords[0],
                tooltip=f"출발: {start_node}",
                icon=folium.Icon(color="red", icon="play", prefix="fa"),
            ).add_to(m)

            folium.Marker(
                coords[-1],
                tooltip=f"도착: {end_node}",
                icon=folium.Icon(color="darkred", icon="flag", prefix="fa"),
            ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


# ============================================================
# 10. 대시보드 1: 시간표 입력 + 지도 요소 선택
# ============================================================

def init_session_state() -> None:
    if "dashboard" not in st.session_state:
        st.session_state.dashboard = "입력/선택 대시보드"

    if "show_food" not in st.session_state:
        st.session_state.show_food = True

    if "show_events" not in st.session_state:
        st.session_state.show_events = True

    for name in RESTAURANT_NAMES:
        key = f"rest_{normalize(name)}"
        if key not in st.session_state:
            st.session_state[key] = True


def dashboard_input_selection() -> None:
    st.title("입력/선택 대시보드")
    st.caption("시간표를 입력하고, 지도에 표시할 요소를 선택하세요.")

    st.subheader("1. 시간표 입력")
    st.write("강좌명, 시간, 장소를 입력합니다. 장소는 `302동`, `26동`처럼 건물번호가 들어가게 작성하면 지도에 표시됩니다.")

    left, right = st.columns(2)

    for i in range(10):
        target_col = left if i < 5 else right

        with target_col:
            with st.container(border=True):
                st.markdown(f"**강의 {i + 1}**")
                st.text_input("강좌명", key=f"course_{i}", placeholder="예: 컴퓨팅 탐색")
                st.text_input("시간 (00:00 - 00:00)", key=f"class_time_{i}", placeholder="예: 09:30 - 10:45")
                st.text_input("장소 (00동)", key=f"class_place_{i}", placeholder="예: 302동")

    st.divider()

    st.subheader("2. 지도 표시 요소 선택")

    with st.container(border=True):
        st.checkbox("식당 + 메뉴", key="show_food")

        if st.session_state.show_food:
            st.write("표시할 식당을 선택하세요. 기본값은 전부 선택입니다.")
            cols = st.columns(3)

            for idx, name in enumerate(RESTAURANT_NAMES):
                with cols[idx % 3]:
                    st.checkbox(name, key=f"rest_{normalize(name)}")

    with st.container(border=True):
        st.checkbox("행사/세미나", key="show_events")
        st.caption(
            "행사/세미나는 Selenium으로 여러 학과 게시판을 열어서 제목, 일시, 장소를 추출합니다. "
            "Chrome 실행 환경이 없으면 결과가 비어 있을 수 있습니다."
        )

    st.divider()

    col1, col2 = st.columns([1, 3])

    with col1:
        st.button(
            "지도 대시보드 열기",
            type="primary",
            use_container_width=True,
            on_click=go_to_map_dashboard,
        )

    with col2:
        entries = parse_schedule_entries()
        st.info(f"현재 입력된 강의: {len(entries)}개")


# ============================================================
# 11. 대시보드 2: 지도
# ============================================================

def selected_restaurants_from_state() -> List[str]:
    if not st.session_state.get("show_food", True):
        return []

    selected = []

    for name in RESTAURANT_NAMES:
        if st.session_state.get(f"rest_{normalize(name)}", True):
            selected.append(name)

    return selected


def schedule_dataframe(entries: Sequence[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "강좌명": e["course"],
                "시간": e["time"],
                "장소": e["place"],
                "건물번호": e["building_no"] or "",
                "지도표시": "O" if e["lat"] is not None else "X",
            }
            for e in entries
        ]
    )


def meal_dataframe(restaurants: Sequence[str], meals: Sequence[Meal]) -> pd.DataFrame:
    meal_type, menu_date = current_meal_slot()
    rows = []

    for name in restaurants:
        restaurant = next((r for r in RESTAURANTS if r.display_name == name), None)
        meal = pick_meal(name, meals, meal_type)

        rows.append(
            {
                "식당": name,
                "위치": restaurant.place if restaurant else "",
                "표시 날짜": menu_date.strftime("%Y.%m.%d"),
                "시간대": meal_type,
                "메뉴": meal.menu if meal else "",
                "가격": meal.price if meal else "",
                "운영시간": meal.operating_time if meal else "",
            }
        )

    return pd.DataFrame(rows)


def events_dataframe(events: Sequence[SeminarEvent]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "행사명": e.title,
                "일시": format_event_time(e.start_dt, e.end_dt),
                "장소": e.place,
                "건물번호": e.building_no or "",
                "지도표시": "O" if e.lat and e.lon else "X",
                "출처": e.source_name,
                "URL": e.source_url,
            }
            for e in events
        ]
    )


def dashboard_map() -> None:
    st.title("지도 대시보드")
    st.caption(
        "정확한 위치 표시는 공식 서울대 캠퍼스맵을 사용하고, "
        "이 앱은 시간표·식당 메뉴·행사/세미나 정보를 함께 보여줍니다."
    )

    st.button(
        "입력/선택 대시보드로 돌아가기",
        on_click=go_to_input_dashboard,
    )

    schedule_entries = parse_schedule_entries()
    selected_restaurants = selected_restaurants_from_state()
    meal_type, menu_date = current_meal_slot()

    raw_meals = crawl_food_menus_cached(meal_type, menu_date.isoformat())
    meals = [Meal(**m) for m in raw_meals]

    events: List[SeminarEvent] = []

    if st.session_state.get("show_events", True):
        with st.spinner("Selenium으로 행사/세미나 크롤링 중입니다. 처음 실행 시 시간이 걸릴 수 있습니다."):
            now_key = datetime.now().strftime("%Y-%m-%d-%H")
            raw_events = crawl_events_with_selenium_cached(now_key, max_links_per_site=50)
            events = restore_events(raw_events)

    st.subheader("공식 서울대 캠퍼스맵")

    components.iframe(
        "https://map.snu.ac.kr/web/main.action",
        height=650,
        scrolling=True,
    )

    st.info(
        "식당과 행사 위치는 아래 표의 장소명을 공식 캠퍼스맵 검색창에 입력해서 확인하세요. "
        "수동 좌표 마커 방식은 실제 위치와 어긋날 수 있어 제거했습니다."
    )

    tab1, tab2, tab3 = st.tabs(["내 시간표", "식당 + 메뉴", "행사/세미나"])

    with tab1:
        st.subheader("내 시간표")

        if schedule_entries:
            st.dataframe(
                schedule_dataframe(schedule_entries),
                use_container_width=True,
                hide_index=True,
            )

            for entry in schedule_entries:
                with st.container(border=True):
                    st.markdown(f"### 📘 {entry['course']}")
                    st.write(f"**시간:** {entry['time']}")
                    st.write(f"**장소:** {entry['place']}")
                    st.link_button(
                        "공식 캠퍼스맵에서 장소 확인",
                        snu_map_search_url(entry["place"]),
                    )
        else:
            st.write("입력된 시간표가 없습니다.")

    with tab2:
        render_restaurant_cards(selected_restaurants, meals)

        st.dataframe(
            meal_dataframe(selected_restaurants, meals),
            use_container_width=True,
            hide_index=True,
        )

    with tab3:
        st.subheader("행사/세미나")
        st.caption(f"수집된 행사/세미나: {len(events)}개")

        event_table = events_dataframe(events)

        if not event_table.empty:
            st.dataframe(event_table, use_container_width=True, hide_index=True)

            for event in events:
                with st.container(border=True):
                    st.markdown(f"### 📅 {event.title}")
                    st.write(f"**일시:** {format_event_time(event.start_dt, event.end_dt)}")
                    st.write(f"**장소:** {event.place or '장소 정보 없음'}")
                    st.write(f"**출처:** {event.source_name}")

                    col1, col2 = st.columns(2)

                    with col1:
                        if event.source_url:
                            st.link_button("원문 보기", event.source_url)

                    with col2:
                        if event.place:
                            st.link_button(
                                "공식 캠퍼스맵에서 장소 확인",
                                snu_map_search_url(event.place),
                            )
        else:
            st.warning(
                "행사/세미나 결과가 없습니다. Chrome/Selenium 실행 환경, 네트워크, 사이트 구조 변경 여부를 확인하세요."
            )



# ============================================================
# 12. 페이지 이동 콜백 + main
# ============================================================

def go_to_map_dashboard() -> None:
    st.session_state["dashboard"] = "지도 대시보드"


def go_to_input_dashboard() -> None:
    st.session_state["dashboard"] = "입력/선택 대시보드"


def main() -> None:
    st.set_page_config(
        page_title="서울대 캠퍼스 지도",
        page_icon="🗺️",
        layout="wide",
    )

    init_session_state()

    st.sidebar.title("서울대 캠퍼스 지도")

    st.sidebar.radio(
        "대시보드",
        ["입력/선택 대시보드", "지도 대시보드"],
        key="dashboard",
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "공식 캠퍼스맵을 함께 열고, 시간표·식당 메뉴·행사/세미나 정보를 표시합니다."
    )

    if st.sidebar.button("크롤링 캐시 삭제"):
        st.cache_data.clear()
        st.rerun()

    if st.session_state["dashboard"] == "입력/선택 대시보드":
        dashboard_input_selection()
    else:
        dashboard_map()


if __name__ == "__main__":
    main()
