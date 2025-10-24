"""
Enhanced Trading Restriction Checker with Addepar Integration
Checks accounts against both trading restrictions and Addepar client list
"""

import pandas as pd
from typing import List
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import base64
import io
import os
import pickle
from datetime import datetime, timedelta
from pathlib import Path

# Import the lightweight Addepar module
from addepar_client_list_only import AddepalClientRetriever

# =====================================================
# CACHING FUNCTIONS FOR ADDEPAR DATA
# =====================================================

CACHE_DIR = Path("cache")
CACHE_FILE = CACHE_DIR / "addepar_clients.pkl"
CACHE_DIR.mkdir(exist_ok=True)


def get_addepar_client_list_cached():
    """
    Get Addepar client list with daily caching.
    Only fetches new data if cache is older than 1 day or doesn't exist.
    """
    need_refresh = False

    # Check if cache exists and its age
    if CACHE_FILE.exists():
        # Get file modification time
        file_mod_time = datetime.fromtimestamp(CACHE_FILE.stat().st_mtime)
        cache_age = datetime.now() - file_mod_time

        # Check if cache is older than 24 hours
        if cache_age > timedelta(hours=24):
            need_refresh = True
            print(f"Cache is {cache_age.total_seconds() / 3600:.1f} hours old. Refreshing...")
        else:
            print(f"Using cached Addepar data ({cache_age.total_seconds() / 3600:.1f} hours old)")
    else:
        need_refresh = True
        print("No cache found. Fetching Addepar data...")

    if need_refresh:
        try:
            # Fetch fresh data from Addepar
            retriever = AddepalClientRetriever()  # Uses ADDEPAR_AUTH env variable
            addepar_df = retriever.get_client_list(
                end_date=datetime.today().strftime("%Y-%m-%d")
            )

            # Save to cache with timestamp
            cache_data = {
                'data': addepar_df,
                'timestamp': datetime.now(),
                'record_count': len(addepar_df)
            }

            with open(CACHE_FILE, 'wb') as f:
                pickle.dump(cache_data, f)

            print(f"Cached {len(addepar_df)} Addepar accounts at {datetime.now()}")
            return addepar_df

        except Exception as e:
            print(f"Error fetching Addepar data: {e}")
            # Try to use existing cache even if expired
            if CACHE_FILE.exists():
                print("Using expired cache due to fetch error")
                with open(CACHE_FILE, 'rb') as f:
                    cache_data = pickle.load(f)
                return cache_data['data']
            else:
                print("No Addepar data available")
                return pd.DataFrame()
    else:
        # Load from cache
        with open(CACHE_FILE, 'rb') as f:
            cache_data = pickle.load(f)
        return cache_data['data']


# =====================================================
# RESTRICTION CHECKING FUNCTIONS
# =====================================================

def check_restrictions_and_addepar(act_no, addepar_accounts):
    """
    Check if account is restricted and if it exists in Addepar.
    Returns a tuple: (is_restricted, in_addepar)
    """
    # Check trading restrictions
    file_loc = "Z:\Shared\Operations\Shared\Custodian Restrictions\Master Trading Restriction Tracker V.3.xlsm"
    try:
        act_data = pd.read_excel(file_loc, sheet_name="Outstanding Restrictions")
        restricted = act_data['Account #'].astype(str).str.replace("-", '').to_list()
        act_no_clean = str(act_no).replace("-", '')
        is_restricted = act_no_clean in restricted
    except Exception as e:
        print(f"Error checking restrictions: {e}")
        is_restricted = None

    # Check if in Addepar
    if not addepar_accounts.empty:
        # Clean account number for comparison
        act_no_clean = str(act_no).replace("-", '')
        if 'Account #' in addepar_accounts.columns:
            addepar_list = addepar_accounts['Account #'].astype(str).str.replace("-", '').to_list()
        elif 'Account Number' in addepar_accounts.columns:
            addepar_list = addepar_accounts['Account Number'].astype(str).str.replace("-", '').to_list()
        else:
            # Try first column if standard names not found
            addepar_list = addepar_accounts.iloc[:, 0].astype(str).str.replace("-", '').to_list()

        in_addepar = act_no_clean in addepar_list
    else:
        in_addepar = None

    return is_restricted, in_addepar


def get_account_status(is_restricted, in_addepar):
    """
    Determine overall account status based on restriction and Addepar checks.
    """
    if in_addepar is None:
        addepar_status = "Addepar Unknown"
    elif not in_addepar:
        return "❌ NOT IN ADDEPAR", "danger"

    if is_restricted is None:
        return "⚠️ RESTRICTION CHECK ERROR", "warning"
    elif is_restricted:
        return "🚫 RESTRICTED", "danger"
    else:
        return "✅ ALL CLEAR", "success"


# =====================================================
# DASH APP
# =====================================================

# Initialize Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Define the app layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("Account Compliance Checker",
                    className="text-center mb-2 text-primary"),
            html.P("Cross-references Trading Restrictions & Addepar Client List",
                   className="text-center text-muted"),
            html.Hr(),
        ], width=12)
    ]),

    # Cache Status Card
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div(id="cache-status", className="text-center")
                ])
            ], className="mb-4", color="light"),
        ], width=12)
    ]),

    # Input Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Single Account Check", className="card-title"),
                    dbc.Input(
                        id="single-account-input",
                        placeholder="Enter account number (e.g., 64314903)",
                        type="text",
                        className="mb-3"
                    ),
                    dbc.Button(
                        "Check Account",
                        id="check-single-button",
                        color="primary",
                        className="w-100",
                        n_clicks=0
                    ),
                ])
            ], className="mb-4"),
        ], width=6),

        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Bulk Account Check", className="card-title"),
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            'Drag and Drop or ',
                            html.A('Select a CSV File')
                        ]),
                        style={
                            'width': '100%',
                            'height': '60px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                            'margin': '10px 0'
                        },
                        multiple=False
                    ),
                    html.Div(id='upload-status', className="mt-2"),
                ])
            ], className="mb-4"),
        ], width=6),
    ]),

    # Refresh Button
    dbc.Row([
        dbc.Col([
            dbc.Button(
                "🔄 Force Refresh Addepar Data",
                id="refresh-addepar-button",
                color="secondary",
                size="sm",
                className="mb-3"
            ),
        ], width=12, className="text-center")
    ]),

    # Output Section
    dbc.Row([
        dbc.Col([
            html.Div(id="output-container", className="mt-4")
        ], width=12)
    ]),

    # Store components
    dcc.Store(id='stored-data'),
    dcc.Store(id='addepar-data'),
    dcc.Interval(id='cache-check-interval', interval=60000, n_intervals=0),  # Check every minute

], fluid=True, className="p-4")


# =====================================================
# CALLBACKS
# =====================================================

# Callback to load and display Addepar cache status
@app.callback(
    Output('addepar-data', 'data'),
    Output('cache-status', 'children'),
    Input('cache-check-interval', 'n_intervals'),
    Input('refresh-addepar-button', 'n_clicks'),
    prevent_initial_call=False
)
def update_addepar_cache(n_intervals, refresh_clicks):
    ctx = dash.callback_context

    # Force refresh if button was clicked
    if ctx.triggered and 'refresh-addepar-button' in ctx.triggered[0]['prop_id']:
        # Delete cache to force refresh
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
            print("Cache deleted. Forcing refresh...")

    # Get Addepar data (cached or fresh)
    addepar_df = get_addepar_client_list_cached()

    # Prepare cache status message
    if CACHE_FILE.exists():
        file_mod_time = datetime.fromtimestamp(CACHE_FILE.stat().st_mtime)
        cache_age = datetime.now() - file_mod_time
        hours_old = cache_age.total_seconds() / 3600

        if hours_old < 1:
            age_str = f"{int(cache_age.total_seconds() / 60)} minutes"
        else:
            age_str = f"{hours_old:.1f} hours"

        status_message = [
            html.Span("📊 Addepar Data: ", className="font-weight-bold"),
            html.Span(f"{len(addepar_df)} accounts | "),
            html.Span(f"Last updated: {age_str} ago | "),
            html.Span(f"Next refresh: {(24 - hours_old):.1f} hours",
                      className="text-muted")
        ]
    else:
        status_message = [
            html.Span("⚠️ No Addepar data available", className="text-warning")
        ]

    # Store Addepar account numbers for quick lookup
    if not addepar_df.empty:
        if 'Account #' in addepar_df.columns:
            account_list = addepar_df['Account #'].astype(str).str.replace("-", '').to_list()
        elif 'Account Number' in addepar_df.columns:
            account_list = addepar_df['Account Number'].astype(str).str.replace("-", '').to_list()
        else:
            account_list = addepar_df.iloc[:, 0].astype(str).str.replace("-", '').to_list()
    else:
        account_list = []

    return account_list, status_message


# Callback for single account check
@app.callback(
    Output('output-container', 'children', allow_duplicate=True),
    Input('check-single-button', 'n_clicks'),
    State('single-account-input', 'value'),
    State('addepar-data', 'data'),
    prevent_initial_call=True
)
def check_single_account(n_clicks, account_number, addepar_accounts):
    if n_clicks == 0 or not account_number:
        return ""

    # Get Addepar DataFrame for checking
    addepar_df = get_addepar_client_list_cached()

    # Check both restrictions and Addepar
    is_restricted, in_addepar = check_restrictions_and_addepar(account_number, addepar_df)
    status_text, status_color = get_account_status(is_restricted, in_addepar)

    # Build detailed message
    details = []
    details.append(html.H4(status_text, className="alert-heading"))
    details.append(html.P(f"Account: {account_number}"))
    details.append(html.Hr())

    # Add detailed status
    details.append(html.Div([
        html.P([
            "• Addepar Status: ",
            html.Strong("✅ Found" if in_addepar else "❌ Not Found",
                        className="text-success" if in_addepar else "text-danger")
        ]),
        html.P([
            "• Trading Status: ",
            html.Strong("🚫 Restricted" if is_restricted else "✅ Clear",
                        className="text-danger" if is_restricted else "text-success")
        ])
    ]))

    alert = dbc.Alert(details, color=status_color, className="mt-3")

    return alert


# Callback for file upload processing
@app.callback(
    Output('stored-data', 'data'),
    Output('upload-status', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def process_upload(contents, filename):
    if contents is None:
        return None, ""

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)

        if 'csv' in filename.lower():
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        else:
            return None, dbc.Alert("Please upload a CSV file.", color="danger", duration=4000)

        # Try to identify the account column
        possible_columns = ['Account', 'Account #', 'Account Number', 'account',
                            'account_number', 'AcctNo', 'Account_No']
        account_col = None

        for col in possible_columns:
            if col in df.columns:
                account_col = col
                break

        if account_col is None:
            account_col = df.columns[0]

        accounts = df[account_col].astype(str).tolist()

        status = dbc.Alert(
            f"✅ Uploaded {filename} with {len(accounts)} accounts",
            color="info",
            duration=4000
        )

        return accounts, status

    except Exception as e:
        return None, dbc.Alert(f"Error processing file: {str(e)}", color="danger", duration=4000)


# Callback for bulk check after file upload
@app.callback(
    Output('output-container', 'children', allow_duplicate=True),
    Input('stored-data', 'data'),
    State('addepar-data', 'data'),
    prevent_initial_call=True
)
def check_bulk_accounts(accounts, addepar_cache):
    if not accounts:
        return ""

    # Get Addepar DataFrame
    addepar_df = get_addepar_client_list_cached()

    # Check all accounts
    results = []
    for acc in accounts:
        is_restricted, in_addepar = check_restrictions_and_addepar(acc, addepar_df)
        status_text, status_color = get_account_status(is_restricted, in_addepar)

        results.append({
            "Account Number": acc,
            "In Addepar": "Yes" if in_addepar else "No",
            "Trading Status": "Restricted" if is_restricted else "Clear",
            "Overall Status": status_text,
            "_status_color": status_color
        })

    # Create DataFrame
    df_results = pd.DataFrame(results)

    # Count issues
    not_in_addepar = sum(1 for r in results if not r["In Addepar"] == "Yes")
    restricted_count = sum(1 for r in results if r["Trading Status"] == "Restricted")
    total_count = len(results)
    clear_count = sum(1 for r in results if "ALL CLEAR" in r["Overall Status"])

    # Create summary alert
    if clear_count == total_count:
        summary_alert = dbc.Alert([
            html.H4("✅ ALL ACCOUNTS CLEAR", className="alert-heading"),
            html.P(f"All {total_count} accounts are in Addepar with no trading restrictions."),
        ], color="success", className="mb-3")
    else:
        alert_items = [
            html.H4("⚠️ ISSUES FOUND", className="alert-heading"),
            html.P(f"Checked {total_count} accounts:"),
            html.Ul([
                html.Li(f"✅ {clear_count} accounts are clear"),
                html.Li(f"❌ {not_in_addepar} accounts not found in Addepar") if not_in_addepar > 0 else None,
                html.Li(f"🚫 {restricted_count} accounts have trading restrictions") if restricted_count > 0 else None,
            ])
        ]
        summary_alert = dbc.Alert(
            [item for item in alert_items if item is not None],
            color="warning" if not_in_addepar > 0 or restricted_count > 0 else "info",
            className="mb-3"
        )

    # Create results table
    table = dash_table.DataTable(
        data=df_results.drop('_status_color', axis=1).to_dict('records'),
        columns=[
            {"name": col, "id": col}
            for col in df_results.columns if col != '_status_color'
        ],
        style_cell={
            'textAlign': 'left',
            'padding': '10px'
        },
        style_data_conditional=[
            {
                'if': {
                    'filter_query': '{Overall Status} contains "ALL CLEAR"',
                },
                'backgroundColor': '#d4edda',
                'color': 'black',
            },
            {
                'if': {
                    'filter_query': '{Overall Status} contains "NOT IN ADDEPAR"',
                },
                'backgroundColor': '#f8d7da',
                'color': 'black',
            },
            {
                'if': {
                    'filter_query': '{Overall Status} contains "RESTRICTED"',
                },
                'backgroundColor': '#fff3cd',
                'color': 'black',
            },
            {
                'if': {
                    'filter_query': '{In Addepar} = "No"',
                    'column_id': 'In Addepar'
                },
                'backgroundColor': '#f8d7da',
                'fontWeight': 'bold',
            },
            {
                'if': {
                    'filter_query': '{Trading Status} = "Restricted"',
                    'column_id': 'Trading Status'
                },
                'backgroundColor': '#fff3cd',
                'fontWeight': 'bold',
            }
        ],
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        sort_action="native",
        filter_action="native",
        page_size=20,
    )

    # Create download button
    download_button = html.Div([
        dbc.Button("📥 Download Results", id="download-button", color="secondary", className="mt-3"),
        dcc.Download(id="download-results")
    ])

    return html.Div([summary_alert, table, download_button])


# Callback for downloading results
@app.callback(
    Output("download-results", "data"),
    Input("download-button", "n_clicks"),
    State('stored-data', 'data'),
    prevent_initial_call=True
)
def download_results(n_clicks, accounts):
    if not accounts:
        return None

    # Get Addepar DataFrame
    addepar_df = get_addepar_client_list_cached()

    # Check all accounts
    results = []
    for acc in accounts:
        is_restricted, in_addepar = check_restrictions_and_addepar(acc, addepar_df)
        status_text, _ = get_account_status(is_restricted, in_addepar)

        results.append({
            "Account Number": acc,
            "In Addepar": "Yes" if in_addepar else "No",
            "Trading Status": "Restricted" if is_restricted else "Clear",
            "Overall Status": status_text.replace("✅", "").replace("❌", "").replace("🚫", "").strip()
        })

    df_export = pd.DataFrame(results)

    return dcc.send_data_frame(df_export.to_csv, "compliance_check_results.csv", index=False)


if __name__ == '__main__':
    # Check if Addepar auth is configured
    if not os.getenv('addepar_auth'):
        print("\n⚠️  WARNING: ADDEPAR_AUTH environment variable not set!")
        print("Set it using: export ADDEPAR_AUTH='username:password'")
        print("The app will run but Addepar checks will not work.\n")

    app.run(debug=True)