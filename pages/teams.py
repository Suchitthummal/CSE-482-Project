

from dash import html, register_page, dcc, dash_table, callback, Input, Output
import pandas as pd
import requests
from dotenv import load_dotenv
import os
import plotly.express as px
import json

load_dotenv()
API_KEY = os.getenv("API_KEY")


def fetch_injuries(API_KEY, league=None, season=None, team=None, player=None):
    api_key = API_KEY

    if not api_key:
        if os.path.exists("saved-output.json"):
            try:
                with open("saved-output.json", "r") as f:
                    data = json.load(f)

                if isinstance(data, dict) and "response" in data and data["response"]:
                    return pd.json_normalize(data["response"])
                elif isinstance(data, list) and data:
                    return pd.json_normalize(data)
                else:
                    return pd.DataFrame()
            except Exception as e:
                print(f"Error reading saved-output.json: {e}")
                return pd.DataFrame()
        else:
            print("No API key and 'saved-output.json' not found. Returning empty DataFrame.")
            return pd.DataFrame()

    url = "https://v3.football.api-sports.io/injuries"

    params = {}
    if league is not None:
        params["league"] = league
    if season is not None:
        params["season"] = season
    if team is not None:
        params["team"] = team
    if player is not None:
        params["player"] = player

    headers = {
        "x-apisports-key": api_key
    }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    try:
        with open("saved-output.json", "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error writing saved-output.json: {e}")

    if "response" not in data or not data["response"]:
        return pd.DataFrame()

    return pd.json_normalize(data["response"])


Df = fetch_injuries(API_KEY, league=39, season=2021)

class APIProcessor:
    def __init__(self):
        self.current_player_info = None
        self.total_players = 594

    def fetch(self, url):
        response = requests.get(url)
        return response.json()

    def get_general_information(self):
        """Loads player list, teams, and position info."""
        url = "https://fantasy.premierleague.com/api/bootstrap-static/"
        plf = (requests.get(url)).json()

        current_team_info = plf['teams']
        self.current_player_info = plf['elements']
        position_info = plf['element_types']

        return self.current_player_info, current_team_info, position_info

    def get_fixtures(self):
        url = "https://fantasy.premierleague.com/api/fixtures/"
        fixture_data = requests.get(url).json()

        team_dict = {
            "1": "Arsenal", "2": "Aston Villa", "3": "Burnley", "4": "Bournemouth", "5": "Brentford",
            "6": "Brighton", "7": "Chelsea", "8": "Crystal Palace", "9": "Everton", "10": "Fulham",
            "11": "Leeds", "12": "Liverpool", "13": "Man City", "14": "Man Utd", "15": "Newcastle",
            "16": "Nott'm Forest", "17": "Sunderland", "18": "Spurs", "19": "West Ham", "20": "Wolves"
        }

        for game in fixture_data:
            if game["event"] is not None:
                game["event"] = f"Gameweek {game['event']}"

            game["team_a"] = team_dict.get(str(game["team_a"]), game["team_a"])
            game["team_h"] = team_dict.get(str(game["team_h"]), game["team_h"])

        return fixture_data

    def get_gameweek_live_data(self):
        gameweeks_data = {}
        for i in range(39):
            url = f"https://fantasy.premierleague.com/api/event/{i}/live/"
            response = requests.get(url).json()
            gameweeks_data[f"Gameweek {i}"] = response
        return gameweeks_data



class InjuryReports:
    def __init__(self):
        api = APIProcessor()

        print("Fetching FPL data...")
        self.current_players_info, self.current_teams_info, self.position_info = api.get_general_information()
        self.fixture_data = api.get_fixtures()
        self.current_gameweek_data = api.get_gameweek_live_data()
        print("Completed Loading FPL Data")

    def to_df(self, data):
        if isinstance(data, pd.DataFrame):
            return data
        return pd.json_normalize(data)


injury_reports = InjuryReports()

players_report = injury_reports.to_df(injury_reports.current_players_info)
team_report = injury_reports.to_df(injury_reports.current_teams_info)
position_report = injury_reports.to_df(injury_reports.position_info)

injury_reports_filtered = players_report[players_report["status"] != "u"]

mapping = {
    'a': 'Available',
    'i': 'Injured',
    'd': 'Doubtful'
}

injury_reports_filtered['status'] = injury_reports_filtered['status'].map(mapping)

important_features = [
    "id", "first_name", "second_name", "web_name",
    "team", "goals_scored", "assists", "saves",
    "element_type",  # position
    "minutes", "starts",
    "status", "news",
    "chance_of_playing_this_round", "chance_of_playing_next_round",
    "yellow_cards", "red_cards",
    "tackles",
    "clearances_blocks_interceptions",
    "recoveries",
    "defensive_contribution", "defensive_contribution_per_90",
    "expected_goals", "expected_assists", "expected_goal_involvements",
    "birth_date",  # to compute age
    "team_join_date"
]

filtered_players = injury_reports_filtered[important_features].copy()

# Map team IDs → team names
team_map = team_report.set_index("id")["name"].to_dict()
filtered_players["team"] = filtered_players["team"].map(team_map)

# Map position IDs → position name
pos_map = position_report.set_index("id")["singular_name_short"].to_dict()
filtered_players.rename(columns={"element_type": "position"}, inplace=True)
filtered_players["position"] = filtered_players["position"].map(pos_map)

# Convert birth_date → age
filtered_players.rename(columns={"birth_date": "age"}, inplace=True)
filtered_players = filtered_players.dropna(subset=["age"])
filtered_players["age"] = filtered_players["age"].apply(
    lambda x: 2025 - int(x.split("-")[0])
)

print(f"Final filtered player count: {len(filtered_players)}")

status_counts = (
    filtered_players
    .pivot_table(index="team", columns="status", aggfunc="size", fill_value=0)
    .reset_index()
)

team_stats = (
    filtered_players.groupby("team")
    .agg({
        "tackles": "sum",
        "yellow_cards": "sum",
        "red_cards": "sum",
        "clearances_blocks_interceptions": "sum",
        "recoveries": "sum",
        "defensive_contribution": "sum",
        "minutes": "sum"
    })
    .reset_index()
)

team_stats = team_stats.merge(status_counts, on="team", how="left")

fixture_report = injury_reports.fixture_data

df_fixtures = injury_reports.to_df(fixture_report)
df_fixtures['date'] = pd.to_datetime(df_fixtures['kickoff_time']).dt.date

fixture_important_features = [
    "event", "finished", "team_a", "team_a_score", "team_h", "team_h_score", "date"
]

df_fixtures = df_fixtures[fixture_important_features]


def build_team_results(fixtures_df, team_stats_df):
    """
    Combine team stats with match results and goal totals.

    fixtures_df columns required:
        ['team_a', 'team_h', 'team_a_score', 'team_h_score']

    team_stats_df:
        contains one row per team
    """
    teams = team_stats_df['team'].unique()
    records = []

    for team_name in teams:
        # Filter matches where team played
        home_matches = fixtures_df.loc[fixtures_df['team_h'] == team_name]
        away_matches = fixtures_df.loc[fixtures_df['team_a'] == team_name]
        matches = pd.concat([home_matches, away_matches])
        matches = matches.sort_values(by='date')

        # Goals for / against
        goals_for = (
            home_matches['team_h_score'].sum() +
            away_matches['team_a_score'].sum()
        )
        goals_against = (
            home_matches['team_a_score'].sum() +
            away_matches['team_h_score'].sum()
        )

        results = []
        for _, row in matches.iterrows():
            if row['team_h'] == team_name:
                home_score = row['team_h_score']
                away_score = row['team_a_score']
            else:
                home_score = row['team_h_score']
                away_score = row['team_a_score']
                home_score, away_score = away_score, home_score

            if home_score > away_score:
                results.append("W")
            elif home_score < away_score:
                results.append("L")
            else:
                results.append("D")

        # Home breakdown
        home_wins = sum(
            (home_matches['team_h_score'] > home_matches['team_a_score']).astype(int)
        )
        home_losses = sum(
            (home_matches['team_h_score'] < home_matches['team_a_score']).astype(int)
        )
        home_draws = sum(
            (home_matches['team_h_score'] == home_matches['team_a_score']).astype(int)
        )

        # Away breakdown
        away_wins = sum(
            (away_matches['team_a_score'] > away_matches['team_h_score']).astype(int)
        )
        away_losses = sum(
            (away_matches['team_a_score'] < away_matches['team_h_score']).astype(int)
        )
        away_draws = sum(
            (away_matches['team_a_score'] == away_matches['team_h_score']).astype(int)
        )

        records.append({
            "team": team_name,
            "total_goals_for": goals_for,
            "total_goals_against": goals_against,
            "results_list": results,
            "home_wins": home_wins,
            "home_losses": home_losses,
            "home_draws": home_draws,
            "away_wins": away_wins,
            "away_losses": away_losses,
            "away_draws": away_draws
        })

    results_df = pd.DataFrame(records)

    final_df = team_stats_df.merge(results_df, on="team", how="left")

    return final_df


team_results = build_team_results(df_fixtures, team_stats)


def process_injury_data(df):
    if df.empty:
        return None, None

    # Extract team name and injury reason
    team_col = None
    reason_col = None

    # Try to find the correct column names
    for col in df.columns:
        if 'team.name' in col.lower() or ('team' in col.lower() and 'name' in col.lower()):
            team_col = col
        if 'player.reason' in col.lower() or ('reason' in col.lower() and 'player' in col.lower()):
            reason_col = col

    if team_col is None:
        possible_team_cols = [col for col in df.columns if 'team' in col.lower()]
        if possible_team_cols:
            team_col = possible_team_cols[0]

    if reason_col is None:
        possible_reason_cols = [col for col in df.columns if 'reason' in col.lower()]
        if possible_reason_cols:
            reason_col = possible_reason_cols[0]

    if team_col is None or reason_col is None:
        return None, None

    # Create a clean dataframe
    injury_df = df[[team_col, reason_col]].copy()
    injury_df.columns = ['Team', 'Injury_Reason']
    injury_df = injury_df.dropna()

    if injury_df.empty:
        return None, None

    # Count injuries by team and reason
    injury_counts = injury_df.groupby(['Team', 'Injury_Reason']).size().reset_index(name='Count')

    # Create summary table: Which team has the most of each injury type
    summary_data = []
    for injury_type in injury_counts['Injury_Reason'].unique():
        injury_subset = injury_counts[injury_counts['Injury_Reason'] == injury_type]
        max_team = injury_subset.loc[injury_subset['Count'].idxmax()]
        summary_data.append({
            'Injury Type': injury_type,
            'Team with Most': max_team['Team'],
            'Count': int(max_team['Count'])
        })

    summary_df = pd.DataFrame(summary_data).sort_values('Count', ascending=False)

    # Create pivot table for heatmap
    pivot_table = injury_counts.pivot(index='Team', columns='Injury_Reason', values='Count').fillna(0)

    # Create heatmap
    fig_heatmap = px.imshow(
        pivot_table.values,
        labels=dict(x="Injury Type", y="Team", color="Number of Injuries"),
        x=pivot_table.columns.tolist(),
        y=pivot_table.index.tolist(),
        color_continuous_scale='Reds',
        aspect="auto",
        title="Team Injury Heatmap: Injuries by Team and Type"
    )
    fig_heatmap.update_layout(
        height=600,
        xaxis_title="Injury Type",
        yaxis_title="Team",
        title_x=0.5
    )

    return summary_df, fig_heatmap


summary_table, heatmap_fig = process_injury_data(Df)


register_page(__name__, path="/teams", name="Team Stats")

defensive_cols = ['tackles', 'recoveries', 'clearances_blocks_interceptions',
                  'defensive_contribution', 'total_goals_against']
attacking_cols = ['total_goals_for', 'home_wins', 'home_losses',
                  'home_draws', 'away_wins', 'away_losses', 'away_draws']

team_dropdown = dcc.Dropdown(
    id='team-dropdown',
    options=[{'label': t, 'value': t} for t in team_results['team']],
    value=team_results['team'].iloc[0],
    clearable=False,
    style={'width': '300px', 'margin': '20px auto'}
)

mode_dropdown = dcc.Dropdown(
    id='mode-dropdown',
    options=[
        {'label': 'Defensive Stats', 'value': 'defense'},
        {'label': 'Attacking Stats', 'value': 'attack'}
    ],
    value='defense',
    clearable=False,
    style={'width': '300px', 'margin': '20px auto'}
)

components = [
    html.H2("Team Dashboard", style={"textAlign": "center", "marginTop": "20px"}),
    team_dropdown,
    mode_dropdown,
    html.Div(id='team-output')  
]

if summary_table is not None and not summary_table.empty:

    if heatmap_fig is not None:
        components.append(
            html.Div([
                html.H3(
                    "Historic Injury Heatmap",
                    style={"textAlign": "center", "marginTop": "30px", "marginBottom": "20px"}
                ),
                dcc.Graph(figure=heatmap_fig)
            ])
        )

    components.append(
        html.Div([
            html.H3(
                "Historic Injury Summary Table",
                style={"textAlign": "center", "marginTop": "40px", "marginBottom": "20px"}
            ),
            dash_table.DataTable(
                data=summary_table.to_dict("records"),
                columns=[{"name": col, "id": col} for col in summary_table.columns],
                style_table={'overflowX': 'auto', 'margin': '20px auto', 'maxWidth': '900px'},
                style_cell={'padding': '10px', 'textAlign': 'left'},
                style_header={'fontWeight': 'bold', 'backgroundColor': '#f0f0f0'},
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#f9f9f9'
                    }
                ]
            )
        ])
    )

layout = html.Div(
    style={"marginTop": "20px", "padding": "20px"},
    children=components
)


@callback(
    Output('team-output', 'children'),
    Input('team-dropdown', 'value'),
    Input('mode-dropdown', 'value')
)
def update_team_dashboard(selected_team, mode):
    # Filter for selected team
    df_team = team_results[team_results['team'] == selected_team]

    # Determine which stats to show
    if mode == 'defense':
        cols = defensive_cols
        title = f"{selected_team} Defensive Stats"
    else:
        cols = attacking_cols
        title = f"{selected_team} Attacking Stats"

    # Bar chart for selected mode
    fig = px.bar(
        x=[col.replace("_", " ").title() for col in cols],
        y=df_team[cols].iloc[0].values,
        labels={'x': 'Stat', 'y': 'Count'},
        title=title
    )

    # Status table
    status_cols = ['Available', 'Doubtful', 'Injured']
    status_table = dash_table.DataTable(
        data=df_team[status_cols].to_dict('records'),
        columns=[{"name": col, "id": col} for col in status_cols],
        style_cell={'textAlign': 'center', 'padding': '5px'},
        style_header={'fontWeight': 'bold', 'backgroundColor': '#f0f0f0'},
        style_data_conditional=[
            {'if': {'filter_query': '{Injured} > 0'}, 'backgroundColor': '#ffe6e6'}
        ]
    )

    # Summary text
    summary_text = html.P(
        f"{selected_team} has {df_team['Available'].values[0]} available players, "
        f"{df_team['Doubtful'].values[0]} doubtful, and {df_team['Injured'].values[0]} injured.",
        style={"textAlign": "center", "fontWeight": "bold", "marginTop": "20px"}
    )

    return [
        dcc.Graph(figure=fig),
        status_table,
        summary_text
    ]
