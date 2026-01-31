import os
import json
from fastapi import FastAPI, HTTPException, Security, Depends, Query
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import HTMLResponse
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- Global Variables ---
API_KEY = os.getenv("API_KEY")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOADS_PATH = os.path.join(BASE_DIR, "loads.json")
HISTORY_PATH = os.path.join(BASE_DIR, "calls_history.json")

# --- Authentication with Api Key ---

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

# Validate API Key from header or query parameter (for dashoard access)
def get_api_key(header: Optional[str] = Security(api_key_header), api_key_query: Optional[str] = None):
    if header == API_KEY or api_key_query == API_KEY:
        return header
    raise HTTPException(status_code=403, detail="Could not validate credentials")

# APP Definition
app = FastAPI(title="Acme Logistics Carrier API", dependencies=[Depends(get_api_key)])

class CallSummary(BaseModel):
    load_id: str
    mc_number: str
    booked: int
    sentiment: str
    original_rate: Optional[int]
    final_rate: Optional[int]
    transcript_summary: str

# --- Endpoints ---
# Search Load Endpoint
@app.get("/search-load")
def search_load(origin: str, destination: str):
    
    # Load loads database
    with open(LOADS_PATH, "r") as f:
        loads_db = json.load(f)

    # Load history database
    with open(HISTORY_PATH, "r") as f:
        history_db = [json.loads(line) for line in f if line.strip()]

    # Searched enabled for origin and destination
    results = [l for l in loads_db if origin.lower() in l["origin"].lower() 
               and destination.lower() in l["destination"].lower()]
    
    booked_ids = {str(h["load_id"]) for h in history_db if h.get("booked") == 1}
    
    results = [r for r in results if str(r["load_id"]) not in booked_ids]
    results.sort(key=lambda x: datetime.strptime(x["pickup_datetime"], "%Y-%m-%dT%H:%M:%S"))
    if not results:
        # Error handling if no loads found
        raise HTTPException(status_code=404, detail="No matching loads found")
    return results[0]

# Call End Endpoint to save call summary
@app.post("/call-end")
def handle_call_end(summary: CallSummary):
    
    # Store the call summary in the history file
    with open(HISTORY_PATH, "a") as f:
        f.write(json.dumps(summary.model_dump()) + "\n")
    
    return {"status": "success", "message": "Call stored"}

# Dashboard Endpoint
@app.get("/dashboard", response_class=HTMLResponse)
def view_dashboard(
    api_key_query: Optional[str] = None, 
    status: Optional[str] = Query(None),
    search_id: Optional[str] = Query(None)
):
    data = []
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, "r") as f:
            data = [json.loads(line) for line in f if line.strip()]

    # Sentiment Mapping
    sentiment_map = {
        "happy": "😊", "positive": "✅", "frustration": "😤", 
        "angry": "😡", "neutral": "😐", "unknown": "😶"
    }

    # Filtering Data Based on Query Params
    if status is not None and status != "":
        try:
            status_val = int(status)
            data = [item for item in data if item.get('booked') == status_val]
        except ValueError:
            pass
    if search_id:
        data = [item for item in data if search_id.lower() in str(item.get('load_id', '')).lower()]

    # --- KPI Calculations ---
    # Total Calls
    total_calls = len(data)

    # Booked Rate
    booked_data = [c for c in data if c.get('booked') == 1]
    booked_rate = (len(booked_data) / total_calls * 100) if total_calls > 0 else 0

    # Average Booked Loads per Carrier
    unique_carriers = set(item.get('mc_number') for item in data if item.get('mc_number'))
    avg_booked_per_carrier = len(booked_data) / len(unique_carriers) if unique_carriers else 0

    # Average Calls per Load
    unique_loads = set(item.get('load_id') for item in data if item.get('load_id'))
    avg_interactions = total_calls / len(unique_loads) if unique_loads else 0

    # Average Calls to Close per Carrier
    close_counts = []
    for b_item in booked_data:
        lid = b_item.get('load_id')
        mc = b_item.get('mc_number')
        if lid and mc:
            interactions = sum(1 for x in data if x.get('load_id') == lid and x.get('mc_number') == mc)
            close_counts.append(interactions)
    avg_calls_to_close = sum(close_counts) / len(close_counts) if close_counts else 0

    # Average Negotiation Percentage for Booked Loads and Sentiment Distribution
    variations = []
    sentiment_counts = {}
    for item in data:
        s_raw = str(item.get('sentiment', 'unknown')).lower()
        emoji = sentiment_map.get(s_raw, "😶")
        s_label = f"{emoji} {s_raw.capitalize()}" 
        sentiment_counts[s_label] = sentiment_counts.get(s_label, 0) + 1
        
        if item.get('booked') == 1:
            orig = item.get('original_rate', 0) / 100.0
            final = item.get('final_rate', 0) / 100.0
            if orig > 0:
                variations.append(((final - orig) / orig) * 100)
    
    avg_negotiation = (sum(variations) / len(variations)) if variations else 0

    # KPI Color Coding
    kpi_color = "#ef4444" if avg_negotiation > 15 else "#f5ca0b" if avg_negotiation > 0 else "#22c55e"

    # HTML / CSS / JS
    html = f"""
    <html>
    <head>
        <title>ACME Logistics Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            html, body {{
                height: 100vh;
                margin: 0;
                padding: 20px 20px;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                background: #f8fafc;
                font-family: 'Inter', sans-serif;
                box-sizing: border-box;
            }}

            .analytics-section {{
                flex: 1; 
                display: flex;
                gap: 20px;
                margin-bottom: 20px;
                min-height: 180px;
                flex-shrink: 0;
            }}

            .management-section {{
                flex: 2;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }}

            .stats-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; flex: 3; }}
            .card {{ 
                background: white; padding: 10px; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
                text-align: center; border-top: 4px solid #3b82f6; display: flex; flex-direction: column; justify-content: center;
            }}
            .card h3 {{ margin: 0; color: #64748b; font-size: 0.65em; text-transform: uppercase; letter-spacing: 0.5px; }}
            .card p {{ font-size: 1.5em; font-weight: bold; margin: 5px 0 0; }}

            .chart-container {{ 
                background: white; padding: 25px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
                flex: 1; max-width: 300px; display: flex; flex-direction: column; align-items: center; min-width: 200px;
            }}

            .filters {{ 
                background: white; padding: 15px; border-radius: 12px; margin-bottom: 15px; 
                box-shadow: 0 1px 3px rgba(0,0,0,0.1); flex-shrink: 0;
            }}

            .table-wrapper {{
                flex-grow: 1;
                overflow-y: auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                border: 1px solid #e2e8f0;
            }}

            table {{ width: 100%; table-layout: fixed; border-collapse: separate; border-spacing: 0; }}
            
            thead th {{
                position: sticky; top: 0; z-index: 10;
                background: #1e293b; color: white; padding: 12px 15px;
                font-size: 0.75em; text-transform: uppercase; text-align: left;
                border-bottom: 0px;
            }}

            td {{ 
                padding: 12px 15px; border-bottom: 1px solid #f1f5f9; font-size: 0.85em; 
                overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
            }}

            tr:hover td {{ background: #f8fafc; }}

            input, select, button {{ padding: 8px 12px; border-radius: 6px; border: 1px solid #e2e8f0; outline: none; }}
            button {{ background: #3b82f6; color: white; border: none; cursor: pointer; font-weight: 600; }}
            button:hover {{ background: #2563eb; }}
            
            .badge {{ padding: 4px 10px; border-radius: 20px; font-size: 0.7em; font-weight: bold; }}
            .status-1 {{ background: #dcfce7; color: #166534; }}
            .status-0 {{ background: #fee2e2; color: #991b1b; }}
            h1, p.subtitle {{ flex-shrink: 0; margin: 0; }}
        </style>
    </head>
    <body>
        <h1 style="margin-bottom: 5px; font-size: 1.5em;">ACME Logistics Carrier Insights</h1>
        <p class="subtitle" style="color: #64748b; margin-bottom: 20px; font-size: 0.9em;">Metrics & Negotiation Analysis</p>

        <div class="analytics-section">
            <div class="stats-grid">
                <div class="card"><h3>Total Calls</h3><p>{total_calls}</p></div>
                <div class="card"><h3>Booked Rate</h3><p>{booked_rate:.1f}%</p></div>
                <div class="card"><h3>Avg. Negotiation</h3><p style="color: {kpi_color}">{avg_negotiation:+.1f}%</p></div>
                <div class="card"><h3>Avg. Calls / Load</h3><p>{avg_interactions:.1f}</p></div>
                <div class="card"><h3>Avg. Calls to Close / Carrier</h3><p>{avg_calls_to_close:.1f}</p></div>
                <div class="card"><h3>Avg. Booked Loads / Carrier</h3><p>{avg_booked_per_carrier:.1f}</p></div>
            </div>
            <div class="chart-container">
                <h3 style="margin: 0 0 10px 0; color: #64748b; font-size: 0.65em; text-transform: uppercase;">Sentiment Distribution</h3>
                <canvas id="sentimentChart"></canvas>
            </div>
        </div>

        <div class="management-section">
            <div class="filters">
                <form method="get" style="display: flex; gap: 15px; align-items: center; margin: 0;">
                    <input type="hidden" name="api_key_query" value="{API_KEY}">
                    <input type="text" name="search_id" style="flex: 1" placeholder="Search by Load ID..." value="{search_id or ''}">
                    <select name="status">
                        <option value="">All Status</option>
                        <option value="1" {"selected" if str(status)=="1" else ""}>Booked</option>
                        <option value="0" {"selected" if str(status)=="0" else ""}>Lost</option>
                    </select>
                    <button type="submit">Filter Results</button>
                    <a href="?api_key_query={API_KEY}" style="color: #64748b; text-decoration: none; font-size: 0.8em;">Reset</a>
                </form>
            </div>

            

            <div class="table-wrapper">
                <table>
                    <colgroup>
                        <col style="width: 12%;"> <col style="width: 10%;"> <col style="width: 12%;">
                        <col style="width: 12%;"> <col style="width: 8%;">  <col style="width: 14%;">
                        <col style="width: 32%;">
                    </colgroup>
                    <thead>
                        <tr>
                            <th>Load ID</th><th>Status</th><th>Initial Rate</th>
                            <th>Final Rate</th><th>Var %</th><th>Sentiment</th><th>Call Summary</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    # Table Rows
    for item in data:
        is_booked = item.get('booked') == 1
        orig = item.get('original_rate', 0) / 100.0
        final = item.get('final_rate', 0) / 100.0
        
        if is_booked and orig > 0:
            var_pct = ((final - orig) / orig * 100)
            var_display = f"{var_pct:+.1f}%"
            trend_color = "#ef4444" if final > orig*1.15 else "#f5ca0b" if final > orig else "#22c55e"
        else:
            var_display = "-"; trend_color = "inherit"

        s_raw = str(item.get('sentiment', '')).lower()
        emoji = sentiment_map.get(s_raw, "😶")
        sentiment_display = f"{emoji} {item.get('sentiment', 'N/A')}"
        summary_text = item.get('transcript_summary', '')
        
        html += f"""
            <tr>
                <td><b>{item.get('load_id')}</b></td>
                <td><span class="badge {'status-1' if is_booked else 'status-0'}">{'BOOKED' if is_booked else 'LOST'}</span></td>
                <td>${orig:.2f}</td>
                <td style="color: {trend_color}; font-weight: bold;">${(final if final > 0 else '-'):.2f}</td>
                <td style="color: {trend_color}; font-weight: bold;">{var_display}</td>
                <td>{sentiment_display}</td>
                <td title="{summary_text}"><small style="color: #64748b;">{summary_text}</small></td>
            </tr>
        """

    # Chart Data
    labels = list(sentiment_counts.keys())
    counts = list(sentiment_counts.values())
    
    html += f"""
                    </tbody>
                </table>
            </div>
        </div>
        <script>
            const ctx = document.getElementById('sentimentChart').getContext('2d');
            new Chart(ctx, {{
                type: 'doughnut',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{
                        data: {json.dumps(counts)},
                        backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#cbd5e1'],
                        borderWidth: 0
                    }}]
                }},
                options: {{ 
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ 
                        legend: {{ position: 'bottom', labels: {{ usePointStyle: true, font: {{ size: 10 }} }} }} 
                    }},
                    cutout: '70%'
                }}
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)