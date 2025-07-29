# AeroLogic ATC Dashboard

A Streamlit-based dashboard for visualizing real-time air traffic, weather, and ATC alerts over Saudi Arabia and the Middle East.

## Features

- Real-time aircraft data from OpenSky Network
- Weather overlays from OpenWeatherMap
- GeoJSON map layers for airports, airspaces, and navigation aids
- ATC alerts (low altitude, separation conflicts)
- Filtering by proximity, country, altitude, and weather
- Interactive map with aircraft icons and tooltips

## Setup

1. **Install Python 3.8+**
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
3. **Run the dashboard:**
   ```sh
   streamlit run dashboard.py
   ```

## API Setup

### First Key - OpenWeatherMap API
For weather data and map overlays, visit [OpenWeatherMap API](https://openweathermap.org/api), sign in to get an API key, and add it to file `dashboard.py`:

```python
OWM_API_KEY = "YOUR_API_KEY_HERE"  # For weather map and data
```

### Second Key - OpenRouter API
For AI alerts and responses, sign up at [OpenRouter.ai](https://openrouter.ai) to get an API key, and add it to file `gpt_risk_checker.py`:

```python
api_key = "YOUR_API_KEY_HERE"  # For AI warnings and alerts
```

## Data Files

- `data/sa_apt.geojson` – Airports
- `data/sa_asp.geojson` – Airspaces
- `data/sa_nav.geojson` – Navigation aids
- `data/sa_frequencies.csv` – ATC frequencies
- `data/sa_airports.csv` – Airport info

## API Keys

- Set your OpenWeatherMap API key in the code (`OWM_API_KEY`).
- Set your OpenRouter API key in `gpt_risk_checker.py` for AI functionality.

## Notes

- Requires internet access for live data.
- For best results, use Chrome or Firefox. 
