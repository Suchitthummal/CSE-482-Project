import pandas as pd
import requests
import concurrent.futures
from dash import html, dcc, register_page, dash_table, callback, Input, Output

from dotenv import load_dotenv
import os
load_dotenv()


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
            "1": "Arsenal","2": "Aston Villa","3": "Burnley","4": "Bournemouth","5": "Brentford",
            "6": "Brighton","7": "Chelsea","8": "Crystal Palace","9": "Everton","10": "Fulham",
            "11": "Leeds","12": "Liverpool","13": "Man City","14": "Man Utd","15": "Newcastle",
            "16": "Nott'm Forest","17": "Sunderland","18": "Spurs","19": "West Ham","20": "Wolves"
        }

        for game in fixture_data:
            if game["event"] is not None:
                game["event"] = f"Gameweek {game['event']}"

            game["team_a"] = team_dict[str(game["team_a"])]
            game["team_h"] = team_dict[str(game["team_h"])]

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

        print("Fetching FPL data")
        self.current_players_info, self.current_teams_info, self.position_info = api.get_general_information()
        self.fixture_data = api.get_fixtures()
        self.current_gameweek_data = api.get_gameweek_live_data()
        print("Completed Loading  Data")

    def to_df(self, data):
        if isinstance(data, pd.DataFrame):
            return data
        return pd.json_normalize(data)



injury_reports = InjuryReports()

players_report = injury_reports.to_df(injury_reports.current_players_info)
team_report = injury_reports.to_df(injury_reports.current_teams_info)
position_report = injury_reports.to_df(injury_reports.position_info)

# Filter players with meaningful status
injury_reports_filtered = players_report[players_report["status"] != "u"]

mapping = {
    'a': 'Available',
    'i': 'Injured',
    'd': 'Doubtful'
}

injury_reports_filtered['status'] = injury_reports_filtered['status'].map(mapping)

important_features = [
    "id", "first_name", "second_name", "web_name",
    "team", "element_type", "goals_scored", "assists", "saves",
    "minutes", "starts",
    "status", "news",
    "chance_of_playing_this_round", "chance_of_playing_next_round",
    "yellow_cards", "red_cards",
    "expected_goals", "expected_assists", "expected_goal_involvements",
    "birth_date", "team_join_date"
]

filtered_players = injury_reports_filtered[important_features].copy()

# Map team IDs team names
team_map = team_report.set_index("id")["name"].to_dict()
filtered_players["team"] = filtered_players["team"].map(team_map)

# Map position IDs position name
pos_map = position_report.set_index("id")["singular_name_short"].to_dict()
filtered_players.rename(columns={"element_type": "position"}, inplace=True)
filtered_players["position"] = filtered_players["position"].map(pos_map)

# Convert birth_date ge
filtered_players.rename(columns={"birth_date": "age"}, inplace=True)
filtered_players = filtered_players.dropna(subset=["age"])
filtered_players["age"] = filtered_players["age"].apply(
    lambda x: 2025 - int(x.split("-")[0])
)

print(f"Final filtered player count: {len(filtered_players)}")


register_page(__name__, path="/players", name="Player Stats")


team_options = [
    {"label": t, "value": t}
    for t in sorted(filtered_players["team"].dropna().unique())
]

position_options = [
    {"label": p, "value": p}
    for p in sorted(filtered_players["position"].dropna().unique())
]

age_min = int(filtered_players["age"].min())
age_max = int(filtered_players["age"].max())


layout = html.Div(
    style={"padding": "24px"},
    children=[
        html.H2("Premier League Player Injury & Status Report"),
        html.P(f"Loaded {len(filtered_players)} players with injury/status info."),

        html.Div(
            style={"display": "flex", "gap": "16px", "marginBottom": "24px"},
            children=[
                # Team filter
                html.Div(
                    style={"flex": "1"},
                    children=[
                        html.Label("Team"),
                        dcc.Dropdown(
                            id="players-team-filter",
                            options=team_options,
                            multi=True,
                            placeholder="Select team(s)",
                        ),
                    ],
                ),

                # Position filter
                html.Div(
                    style={"flex": "1"},
                    children=[
                        html.Label("Position"),
                        dcc.Dropdown(
                            id="players-position-filter",
                            options=position_options,
                            multi=True,
                            placeholder="Select position(s)",
                        ),
                    ],
                ),

                # Age filter
                html.Div(
                    style={"flex": "1"},
                    children=[
                        html.Label(f"Age Range ({age_min}-{age_max})"),
                        dcc.RangeSlider(
                            id="players-age-filter",
                            min=age_min,
                            max=age_max,
                            step=1,
                            value=[age_min, age_max],
                            tooltip={"placement": "bottom", "always_visible": False},
                        ),
                    ],
                ),
            ],
        ),

        html.Div(
            style={"display": "flex", "gap": "24px", "marginBottom": "24px"},
            children=[
                html.Div(
                    style={"width": "300px"},
                    children=[
                        html.Label("Select Player"),
                        dcc.Dropdown(
                            id="player-dropdown",
                            options=[],  
                            placeholder="Choose a player",
                        ),
                    ],
                ),
                html.Div(
                    id="player-profile",
                    style={
                        "flex": "1",
                        "border": "1px solid #ddd",
                        "borderRadius": "8px",
                        "padding": "16px",
                        "minHeight": "120px",
                    },
                    children=[
                        html.I("Select a player to see details.")
                    ],
                ),
            ],
        ),

        dash_table.DataTable(
            id="players-table",
            data=filtered_players.to_dict("records"),
            columns=[
                {"name": "Name", "id": "web_name"},
                {"name": "Team", "id": "team"},
                {"name": "Pos", "id": "position"},
                {"name": "Age", "id": "age"},
                {"name": "Minutes", "id": "minutes"},
                {"name": "Starts", "id": "starts"},
                {"name": "Status", "id": "status"},
                {"name": "News", "id": "news"},
                {"name": "Goals", "id": "goals_scored"},
                {"name": "xG", "id": "expected_goals"},
                {"name": "Assists", "id": "assists"},
                {"name": "xA", "id": "expected_assists"},
                {"name": "xGI", "id": "expected_goal_involvements"},
                {"name": "Saves", "id": "saves"},
                {"name": "Yellow", "id": "yellow_cards"},
                {"name": "Red", "id": "red_cards"},
            ],
            page_size=20,
            style_table={"overflowX": "auto"},
            style_cell={"padding": "6px", "textAlign": "left", "fontSize": 12},
            style_header={"fontWeight": "bold"},
            sort_action="native",
            filter_action="native",
        ),
    ],
)



@callback(
    Output("players-table", "data"),
    Output("player-dropdown", "options"),
    Input("players-team-filter", "value"),
    Input("players-position-filter", "value"),
    Input("players-age-filter", "value"),
)
def update_players_view(selected_teams, selected_positions, age_range):
    df = filtered_players.copy()

    # Team filter
    if selected_teams:
        df = df[df["team"].isin(selected_teams)]

    # Position filter
    if selected_positions:
        df = df[df["position"].isin(selected_positions)]

    # Age filter
    if age_range and len(age_range) == 2:
        min_age, max_age = age_range
        df = df[(df["age"] >= min_age) & (df["age"] <= max_age)]

    # Dropdown options based on filtered df
    dropdown_options = [
        {
            "label": f"{row['web_name']} ({row['team']} - {row['position']})",
            "value": int(row["id"]),
        }
        for _, row in df.iterrows()
    ]

    return df.to_dict("records"), dropdown_options



@callback(
    Output("player-profile", "children"),
    Input("player-dropdown", "value"),
)
def update_player_profile(selected_player_id):
    if selected_player_id is None:
        return html.I("Select a player to see details.")

    row = filtered_players[filtered_players["id"] == selected_player_id]
    if row.empty:
        return html.I("Player not found in current data.")

    row = row.iloc[0]

    return html.Div(
        children=[
            html.H3(f"{row['first_name']} {row['second_name']} ({row['web_name']})"),
            html.P(f"Team: {row['team']}"),
            html.P(f"Position: {row['position']} • Age: {row['age']}"),
            html.P(f"Status: {row['status'] or 'N/A'}"),
            html.P(f"News: {row['news'] or 'No news'}"),
            html.H4("Performance"),
            html.Ul(
                children=[
                    html.Li(f"Minutes: {row['minutes']}"),
                    html.Li(f"Starts: {row['starts']}"),
                    html.Li(f"Goals: {row['goals_scored']}"),
                    html.Li(f"xG: {row['expected_goals']}"),
                    html.Li(f"Assists: {row['assists']}"),
                    html.Li(f"xA: {row['expected_assists']}"),
                    html.Li(f"xGI: {row['expected_goal_involvements']}"),
                    html.Li(f"Saves: {row['saves']}"),
                    html.Li(f"Yellow cards: {row['yellow_cards']}"),
                    html.Li(f"Red cards: {row['red_cards']}"),
                ]
            ),
            html.P(f"Team join date: {row['team_join_date']}"),
        ]
    )
