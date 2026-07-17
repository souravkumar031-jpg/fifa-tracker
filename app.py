import streamlit as st
import sqlite3
import pandas as pd
import json
import google.generativeai as genai
from PIL import Image
import os

st.set_page_config(page_title="FIFA Tracker", page_icon="⚽", layout="wide")

# Database Setup
DB_FILE = "world_cup_stats.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS matches (id INTEGER PRIMARY KEY AUTOINCREMENT, home_team TEXT, away_team TEXT, home_score INTEGER, away_score INTEGER, possession_home INTEGER, possession_away INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS player_stats (id INTEGER PRIMARY KEY AUTOINCREMENT, match_id INTEGER, player_name TEXT, team TEXT, goals INTEGER DEFAULT 0, assists INTEGER DEFAULT 0, yellow_cards INTEGER DEFAULT 0, red_cards INTEGER DEFAULT 0, fouls_committed INTEGER DEFAULT 0, dribbles_completed INTEGER DEFAULT 0, rating REAL DEFAULT 6.0, FOREIGN KEY(match_id) REFERENCES matches(id))''')
    conn.commit()
    conn.close()

init_db()

def parse_screenshot(uploaded_file, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    img = Image.open(uploaded_file)
    prompt = """
    Analyze this football match stats screenshot. Extract the overall match metrics and individual player data.
    You must output ONLY a valid JSON object matching the exact format schema below. Do not wrap it in markdown block quotes.
    {
      "home_team": "Team Name", "away_team": "Team Name", "home_score": 0, "away_score": 0,
      "possession_home": 50, "possession_away": 50,
      "players": [
        {"player_name": "Player Name", "team": "Team Name", "goals": 0, "assists": 0, "yellow_cards": 0, "red_cards": 0, "fouls_committed": 0, "dribbles_completed": 0, "rating": 6.5}
      ]
    }
    """
    response = model.generate_content([prompt, img])
    clean_text = response.text.strip().replace("```json", "").replace("```", "")
    return json.loads(clean_text)
# UI Setup
st.title("🏆 FIFA Tournament Center")
st.markdown("---")

menu = ["📊 Leaderboards", "📤 Upload Match Center", "📋 Match Log"]
choice = st.sidebar.selectbox("Navigate Windows", menu)

if choice == "📊 Leaderboards":
    st.header("🏅 Tournament Leaderboards")
    conn = sqlite3.connect(DB_FILE)
    tab1, tab2, tab3, tab4 = st.tabs(["🥾 Golden Boot", "🎯 Most Assists", "⭐ Highest Player Ratings", "🟨 Disciplinary Room"])
    
    with tab1:
        df = pd.read_sql_query('SELECT player_name AS Player, team AS Country, SUM(goals) AS Goals FROM player_stats GROUP BY Player, Country HAVING Goals > 0 ORDER BY Goals DESC', conn)
        st.dataframe(df, use_container_width=True, hide_index=True)
    with tab2:
        df = pd.read_sql_query('SELECT player_name AS Player, team AS Country, SUM(assists) AS Assists FROM player_stats GROUP BY Player, Country HAVING Assists > 0 ORDER BY Assists DESC', conn)
        st.dataframe(df, use_container_width=True, hide_index=True)
    with tab3:
        df = pd.read_sql_query('SELECT player_name AS Player, team AS Country, ROUND(AVG(rating), 2) AS "Avg Rating", COUNT(match_id) AS "Matches Played" FROM player_stats GROUP BY Player, Country ORDER BY "Avg Rating" DESC', conn)
        st.dataframe(df, use_container_width=True, hide_index=True)
    with tab4:
        df = pd.read_sql_query('SELECT player_name AS Player, team AS Country, SUM(yellow_cards) AS "Yellow Cards", SUM(red_cards) AS "Red Cards", SUM(fouls_committed) AS "Fouls Committed" FROM player_stats GROUP BY Player, Country ORDER BY "Red Cards" DESC, "Yellow Cards" DESC', conn)
        st.dataframe(df, use_container_width=True, hide_index=True)
    conn.close()

elif choice == "📤 Upload Match Center":
    st.header("📸 Automated Stats Capture")
    st.info("Your Gemini API Key is required to read screenshots.")
    user_api_key = st.text_input("Enter your Gemini API Key:", type="password")
    
    uploaded_file = st.file_uploader("Upload Image...", type=["png", "jpg", "jpeg"])
    if uploaded_file and user_api_key:
        st.image(uploaded_file, caption="Preview", width=300)
        if st.button("🚀 Process & Categorize Stats"):
            with st.spinner("AI sorting data..."):
                try:
                    data = parse_screenshot(uploaded_file, user_api_key)
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute('INSERT INTO matches (home_team, away_team, home_score, away_score, possession_home, possession_away) VALUES (?, ?, ?, ?, ?, ?)', (data['home_team'], data['away_team'], data['home_score'], data['away_score'], data['possession_home'], data['possession_away']))
                    match_id = cursor.lastrowid
                    for p in data['players']:
                        cursor.execute('INSERT INTO player_stats (match_id, player_name, team, goals, assists, yellow_cards, red_cards, fouls_committed, dribbles_completed, rating) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (match_id, p['player_name'], p['team'], p.get('goals',0), p.get('assists',0), p.get('yellow_cards',0), p.get('red_cards',0), p.get('fouls_committed',0), p.get('dribbles_completed',0), p.get('rating',6.0)))
                    conn.commit()
                    conn.close()
                    st.success(f"Log Successful: {data['home_team']} vs {data['away_team']}")
                    st.json(data)
                except Exception as e:
                    st.error(f"Error: {e}")

elif choice == "📋 Match Log":
    st.header("📅 Match History")
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query('SELECT id AS "Match ID", home_team AS "Home Team", home_score AS "🏠 Score", away_score AS "⚽ Score", away_team AS "Away Team" FROM matches ORDER BY id DESC', conn)
    st.dataframe(df, use_container_width=True, hide_index=True)
    conn.close()
