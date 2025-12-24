import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import os

# Example: load signals + survey data
signals = pd.read_csv("signals.csv")  # columns: time, SpO2, HeartRate_bpm, NasalPressure, Flow, RIPFlow, PosAngle, X, Y, Z
surveys = pd.read_csv("surveys.csv")  # columns: PatientID, Age, BMI, ComfortScore, Comments

# Add PatientID to signals data (assuming this is Patient 101)
signals['PatientID'] = 101

# Map new column names to expected names for compatibility
signals['Time'] = signals['time']
signals['Airflow'] = signals['NasalPressure']  # Nasal pressure represents airflow
signals['Effort'] = signals['RIPFlow']  # Respiratory effort
signals['Suction'] = 0.5  # Placeholder - adjust based on device settings
signals['HeartRate'] = signals['HeartRate_bpm']

# Additional sample data for other pages
device_settings_data = {
    'PatientID': [101, 102, 103, 104, 105],
    'DeviceModel': ['OSA-Pro 3000', 'OSA-Pro 3000', 'OSA-Advanced 4000', 'OSA-Pro 3000', 'OSA-Advanced 4000'],
    'SuctionPressure': [12.5, 15.2, 18.0, 14.8, 16.5],
    'AutoMode': [True, False, True, True, False],
    'RampTime': [20, 15, 30, 25, 20],
    'LeakCompensation': [True, True, False, True, True],
    'LastCalibration': ['2024-01-15', '2024-01-20', '2024-01-18', '2024-01-22', '2024-01-19'],
    'DeviceStatus': ['Active', 'Active', 'Maintenance', 'Active', 'Active'],
    'FirmwareVersion': ['v2.1.3', 'v2.1.3', 'v2.2.1', 'v2.1.3', 'v2.2.1']
}

sleep_analysis_data = {
    'PatientID': [101, 102, 103, 104, 105],
    'TotalSleepTime': [7.2, 6.8, 5.5, 7.8, 6.2],
    'SleepEfficiency': [85.3, 78.2, 62.1, 91.4, 73.8],
    'REMPercentage': [18.5, 22.1, 15.2, 20.8, 19.3],
    'DeepSleepPercentage': [15.2, 12.8, 8.9, 18.1, 13.4],
    'LightSleepPercentage': [66.3, 65.1, 75.9, 61.1, 67.3],
    'ArousalsPerHour': [12.3, 18.7, 28.4, 8.9, 15.6],
    'SleepLatency': [8.2, 15.4, 32.1, 6.8, 12.9],
    'WakeAfterSleepOnset': [45.2, 62.8, 98.4, 28.1, 51.7],
    'SleepQualityScore': [8.2, 6.8, 4.1, 9.1, 7.3]
}

device_settings_df = pd.DataFrame(device_settings_data)
sleep_analysis_df = pd.DataFrame(sleep_analysis_data)

# Merge survey data with signals for each time point
signals_with_survey = signals.merge(surveys, on='PatientID', how='left')

# Add contextual information for hover tooltips
def add_contextual_info(row):
    """Add contextual information based on signal values"""
    context = []
    
    # SpO2 context
    if row['SpO2'] < 90:
        context.append("Desaturation - may have felt breathless")
    elif row['SpO2'] < 95:
        context.append("Low oxygen - may have felt tired")
    
    # Airflow context
    if row['Airflow'] < 0.2:
        context.append("Apnea - breathing pause likely")
    elif row['Airflow'] < 0.5:
        context.append("Shallow breathing - may have felt restless")
    
    # Suction context
    if row['Suction'] > 0.8:
        context.append("High suction - jaw pressure")
    elif row['Suction'] < 0.3:
        context.append("Low suction - device may have loosened")
    
    # Comfort context
    if row['ComfortScore'] < 5:
        context.append("Low comfort - significant discomfort")
    elif row['ComfortScore'] < 7:
        context.append("Moderate comfort - some discomfort")
    else:
        context.append("Good comfort - comfortable sleep")
    
    return " | ".join(context) if context else "Normal sleep patterns"

signals_with_survey['ContextualInfo'] = signals_with_survey.apply(add_contextual_info, axis=1)

# External stylesheets for medical dashboard styling
external_stylesheets = [
    'https://codepen.io/chriddyp/pen/bWLwgP.css',
    '/assets/style.css'
]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# Set the server for deployment
server = app.server

app.layout = html.Div([
    # Store component for navigation state
    dcc.Store(id='current-page', data='overview'),
    
    # Header Section
    html.Div([
        html.Div([
            html.H1("Sleep Apnea Monitoring Dashboard - Version 2", 
                   style={'color': '#000000', 'margin': '0', 'fontSize': '2.5rem', 'fontWeight': '400', 'letterSpacing': '-0.03em', 'lineHeight': '1.1'}),
            html.P("Real-time Patient Monitoring & Analysis - Enhanced Version", 
                  style={'color': '#666666', 'margin': '8px 0 0 0', 'fontSize': '16px', 'fontWeight': '400', 'lineHeight': '1.4'})
        ], style={'flex': '1'}),
        
        html.Div([
            html.Label("Patient ID", style={'color': '#666666', 'fontSize': '16px', 'fontWeight': '400', 'marginBottom': '8px', 'lineHeight': '1.4'}),
            dcc.Dropdown(
                id="patient-dropdown",
                options=[{"label": f"Patient {pid}", "value": pid} for pid in signals_with_survey["PatientID"].unique()],
                value=signals_with_survey["PatientID"].unique()[0],
                style={'width': '200px'},
                className="patient-dropdown"
            )
        ], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'flex-end'})
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'flex-start'}, className="dashboard-header"),
    
    # Main Content Area
    html.Div([
        # Sidebar Navigation
        html.Div([
            html.H3("Navigation", style={'color': '#000000', 'marginBottom': '24px', 'fontSize': '1.5rem', 'fontWeight': '400', 'letterSpacing': '-0.02em', 'lineHeight': '1.2'}),
            html.Div([
                html.Div("Overview", id="nav-overview", className="nav-item active", n_clicks=0),
                html.Div("Patient Details", id="nav-patient-details", className="nav-item", n_clicks=0),
                html.Div("Sleep Analysis", id="nav-sleep-analysis", className="nav-item", n_clicks=0),
                html.Div("Device Settings", id="nav-device-settings", className="nav-item", n_clicks=0),
                html.Div("Reports", id="nav-reports", className="nav-item", n_clicks=0),
                html.Div("Settings", id="nav-settings", className="nav-item", n_clicks=0)
            ]),
            
            html.Hr(style={'borderColor': '#e2e8f0', 'margin': '32px 0'}),
            
            html.H4("Quick Stats - V2", style={'color': '#000000', 'marginBottom': '20px', 'fontSize': '1.25rem', 'fontWeight': '400', 'letterSpacing': '-0.01em', 'lineHeight': '1.3'}),
            html.Div([
                html.P(f"Total Patients: {len(signals_with_survey['PatientID'].unique())}", 
                      style={'color': '#666666', 'margin': '12px 0', 'fontSize': '16px', 'fontWeight': '400', 'lineHeight': '1.4'}),
                html.P(f"Active Sessions: {len(signals_with_survey)}", 
                      style={'color': '#666666', 'margin': '12px 0', 'fontSize': '16px', 'fontWeight': '400', 'lineHeight': '1.4'}),
                html.P("Enhanced Version: 2.0", 
                      style={'color': '#2563eb', 'margin': '12px 0', 'fontSize': '16px', 'fontWeight': '400', 'lineHeight': '1.4'})
            ])
        ], className="sidebar"),
        
        # Main Content Area
        html.Div(id="main-content", className="content-area")
    ], className="main-content")
], className="dashboard-container")

# All the callback functions (same as original but with enhanced features)
@app.callback(
    [Output('current-page', 'data'),
     Output('nav-overview', 'className'),
     Output('nav-patient-details', 'className'),
     Output('nav-sleep-analysis', 'className'),
     Output('nav-device-settings', 'className'),
     Output('nav-reports', 'className'),
     Output('nav-settings', 'className')],
    [Input('nav-overview', 'n_clicks'),
     Input('nav-patient-details', 'n_clicks'),
     Input('nav-sleep-analysis', 'n_clicks'),
     Input('nav-device-settings', 'n_clicks'),
     Input('nav-reports', 'n_clicks'),
     Input('nav-settings', 'n_clicks')],
    prevent_initial_call=True
)
def update_navigation(overview_clicks, patient_clicks, sleep_clicks, device_clicks, reports_clicks, settings_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return 'overview', 'nav-item active', 'nav-item', 'nav-item', 'nav-item', 'nav-item', 'nav-item'
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Reset all nav items
    nav_classes = ['nav-item'] * 6
    
    if button_id == 'nav-overview':
        page = 'overview'
        nav_classes[0] = 'nav-item active'
    elif button_id == 'nav-patient-details':
        page = 'patient-details'
        nav_classes[1] = 'nav-item active'
    elif button_id == 'nav-sleep-analysis':
        page = 'sleep-analysis'
        nav_classes[2] = 'nav-item active'
    elif button_id == 'nav-device-settings':
        page = 'device-settings'
        nav_classes[3] = 'nav-item active'
    elif button_id == 'nav-reports':
        page = 'reports'
        nav_classes[4] = 'nav-item active'
    elif button_id == 'nav-settings':
        page = 'settings'
        nav_classes[5] = 'nav-item active'
    else:
        page = 'overview'
        nav_classes[0] = 'nav-item active'
    
    return page, *nav_classes

@app.callback(
    Output("main-content", "children"),
    [Input("patient-dropdown", "value"),
     Input("current-page", "data")]
)
def update_dashboard(patient_id, current_page):
    if not patient_id:
        return html.Div("Please select a patient")
    
    # Route to different pages
    if current_page == 'overview':
        return create_overview_page(patient_id)
    elif current_page == 'patient-details':
        return create_patient_details_page(patient_id)
    elif current_page == 'sleep-analysis':
        return create_sleep_analysis_page(patient_id)
    elif current_page == 'device-settings':
        return create_device_settings_page(patient_id)
    elif current_page == 'reports':
        return create_reports_page(patient_id)
    elif current_page == 'settings':
        return create_settings_page(patient_id)
    else:
        return create_overview_page(patient_id)

def create_overview_page(patient_id):
    return html.Div([
        html.H2(f"Enhanced Overview - Patient {patient_id}", className="section-title"),
        html.Div([
            html.H3("Version 2 Dashboard", style={'marginBottom': '20px', 'color': '#2563eb'}),
            html.P("✨ This is the enhanced Version 2 of the Sleep Apnea Dashboard", className="body-text"),
            html.P("🔍 Features advanced analytics and improved monitoring", className="body-text"),
            html.P("📊 Enhanced visualizations and reporting capabilities", className="body-text"),
            html.P("🚀 Running on port 8051 for parallel development", className="body-text")
        ], className="metric-card")
    ])

def create_patient_details_page(patient_id):
    return html.Div([
        html.H2(f"Enhanced Patient Details - Patient {patient_id}", className="section-title"),
        html.Div([
            html.H3("Version 2 Patient Information", style={'marginBottom': '20px'}),
            html.P("Enhanced patient details coming soon", className="body-text")
        ], className="metric-card")
    ])

def create_sleep_analysis_page(patient_id):
    return html.Div([
        html.H2(f"Enhanced Sleep Analysis - Patient {patient_id}", className="section-title"),
        html.Div([
            html.H3("Version 2 Sleep Analytics", style={'marginBottom': '20px'}),
            html.P("Advanced sleep analysis features", className="body-text")
        ], className="metric-card")
    ])

def create_device_settings_page(patient_id):
    return html.Div([
        html.H2(f"Enhanced Device Settings - Patient {patient_id}", className="section-title"),
        html.Div([
            html.H3("Version 2 Device Management", style={'marginBottom': '20px'}),
            html.P("Enhanced device configuration options", className="body-text")
        ], className="metric-card")
    ])

def create_reports_page(patient_id):
    return html.Div([
        html.H2(f"Enhanced Reports - Patient {patient_id}", className="section-title"),
        html.Div([
            html.H3("Version 2 Reporting", style={'marginBottom': '20px'}),
            html.P("Advanced reporting capabilities", className="body-text")
        ], className="metric-card")
    ])

def create_settings_page(patient_id):
    return html.Div([
        html.H2("Enhanced Dashboard Settings", className="section-title"),
        html.Div([
            html.H3("Version 2 Settings", style={'marginBottom': '20px'}),
            html.P("Enhanced configuration options", className="body-text")
        ], className="metric-card")
    ])

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8054)  # Prototype 4 server
