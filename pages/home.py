from dash import html, dcc, register_page

register_page(__name__, path="/", name="Home")

layout = html.Div(
    style={"fontFamily": "Arial", "textAlign": "center", "marginTop": "60px"},
    children=[
        html.H1("Premier League Stats", style={"fontSize": "40px"}),

        html.Div(
            [
                dcc.Link(
                    html.Button(
                        "Team Stats",
                        style={
                            "padding": "20px 40px",
                            "fontSize": "20px",
                            "margin": "20px",
                            "cursor": "pointer",
                        },
                    ),
                    href="/teams",
                ),
                dcc.Link(
                    html.Button(
                        "Player Stats",
                        style={
                            "padding": "20px 40px",
                            "fontSize": "20px",
                            "margin": "20px",
                            "cursor": "pointer",
                        },
                    ),
                    href="/players",
                ),
            ]
        ),
    ],
)
