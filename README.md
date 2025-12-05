# CSE-482-Project

A Premier League statistics dashboard built with Dash that provides comprehensive player and team analytics, injury reports, and match fixtures.

## Features

- **Home Page**: Navigation hub with links to Team Stats and Player Stats
- **Player Stats Page**: 
  - Filter players by team, position, and age
  - View detailed player profiles with performance metrics
  - Track player injury status and availability
  - Display goals, assists, expected goals (xG), expected assists (xA), and more
- **Team Stats Page**:
  - View defensive and attacking statistics by team
  - Analyze team injury patterns with interactive heatmaps
  - Track team performance metrics including goals for/against, wins, losses, draws
  - Historical injury summary tables

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd CSE-482-Project
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Set up environment variables:
   - Create a `.env` file in the project root
   - Add your API key for the football API (if using):
   ```
   API_KEY=your_api_key_here
   ```
   - Note: The application will work with cached data from `saved-output.json` if no API key is provided

## Usage

Run the application:
```bash
python app.py
```

The application will start on `http://127.0.0.1:8050` (default Dash port).

Open your browser and navigate to the URL to access the dashboard.

## Project Structure

```
CSE-482-Project/
├── app.py                 # Main Dash application entry point
├── pages/
│   ├── home.py           # Home page with navigation
│   ├── players.py        # Player statistics and filtering page
│   └── teams.py          # Team statistics and injury analysis page
├── requirements.txt      # Python dependencies
├── saved-output.json    # Cached API response data
└── README.md            # This file
```

## Dependencies

- **dash** (>=2.14.0): Web framework for building interactive dashboards
- **pandas** (>=2.0.0): Data manipulation and analysis
- **requests** (>=2.31.0): HTTP library for API calls
- **python-dotenv** (>=1.0.0): Environment variable management
- **plotly** (>=5.17.0): Interactive data visualization

## Data Sources

- **Fantasy Premier League API**: Player statistics, team information, fixtures, and gameweek data "https://fantasy.premierleague.com/api/bootstrap-static/"
- **Football API (API-Sports.io)**: Historical injury data (optional, requires API key) "https://v3.football.api-sports.io/injuries"

