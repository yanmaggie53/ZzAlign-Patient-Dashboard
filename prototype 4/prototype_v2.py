import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

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
            
            html.H4("Quick Stats", style={'color': '#000000', 'marginBottom': '20px', 'fontSize': '1.25rem', 'fontWeight': '400', 'letterSpacing': '-0.01em', 'lineHeight': '1.3'}),
            html.Div([
                html.P(f"Total Patients: {len(signals_with_survey['PatientID'].unique())}", 
                      style={'color': '#666666', 'margin': '12px 0', 'fontSize': '16px', 'fontWeight': '400', 'lineHeight': '1.4'}),
                html.P(f"Active Sessions: {len(signals_with_survey)}", 
                      style={'color': '#666666', 'margin': '12px 0', 'fontSize': '16px', 'fontWeight': '400', 'lineHeight': '1.4'}),
                html.P("Last Updated: Now", 
                      style={'color': '#666666', 'margin': '12px 0', 'fontSize': '16px', 'fontWeight': '400', 'lineHeight': '1.4'})
            ])
        ], className="sidebar"),
        
        # Main Content Area
        html.Div(id="main-content", className="content-area")
    ], className="main-content")
], className="dashboard-container")

# Navigation callback
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
    patient_data = signals_with_survey[signals_with_survey["PatientID"] == patient_id]
    
    if len(patient_data) == 0:
        return html.Div(f"No data available for Patient {patient_id}")
    
    # Get survey data (same for all time points for this patient)
    patient_survey = patient_data.iloc[0] if len(patient_data) > 0 else None
    
    # Calculate summary metrics
    mean_spo2 = patient_data['SpO2'].mean()
    min_spo2 = patient_data['SpO2'].min()
    mean_suction = patient_data['Suction'].mean()
    suction_stability = 1 - (patient_data['Suction'].std() / patient_data['Suction'].mean()) if patient_data['Suction'].mean() > 0 else 0
    
    # Count desaturation events
    desat_events = len(patient_data[patient_data['SpO2'] < 90])
    
    # Count apnea events (airflow < 0.2)
    apnea_events = len(patient_data[patient_data['Airflow'] < 0.2])
    
    # Calculate AHI (events per hour - simplified)
    ahi_with_device = (apnea_events / (patient_data['Time'].max() / 60)) if patient_data['Time'].max() > 0 else 0
    ahi_without_device = ahi_with_device * 1.5  # Estimated baseline
    
    # Create comprehensive timeline plot
    fig = create_timeline_plot(patient_data, patient_id)
    
    # Create side panel with patient context
    side_panel = create_side_panel(patient_survey, patient_id)
    
    return html.Div([
        # Top row: Key metrics cards
        html.Div([
            html.Div([
                html.Div([
                    html.P(f"{mean_spo2:.1f}%", className="metric-value"),
                    html.P("Mean SpO₂", className="metric-label")
                ], className="metric-card", style={'textAlign': 'center', 'flex': '1'}),
                
                html.Div([
                    html.P(f"{min_spo2:.1f}%", className="metric-value status-danger" if min_spo2 < 90 else "metric-value status-good"),
                    html.P("Nadir SpO₂", className="metric-label")
                ], className="metric-card", style={'textAlign': 'center', 'flex': '1'}),
                
                html.Div([
                    html.P(f"{desat_events}", className="metric-value status-warning" if desat_events > 0 else "metric-value status-good"),
                    html.P("Desaturation Events", className="metric-label")
                ], className="metric-card", style={'textAlign': 'center', 'flex': '1'}),
                
                html.Div([
                    html.P(f"{ahi_with_device:.1f}/hr", className="metric-value status-good" if ahi_with_device < 5 else "metric-value status-danger"),
                    html.P("AHI with Device", className="metric-label")
                ], className="metric-card", style={'textAlign': 'center', 'flex': '1'}),
                
                html.Div([
                    html.P(f"{suction_stability:.2f}", className="metric-value status-good" if suction_stability > 0.8 else "metric-value status-warning"),
                    html.P("Suction Stability", className="metric-label")
                ], className="metric-card", style={'textAlign': 'center', 'flex': '1'})
            ], style={'display': 'flex', 'gap': '16px', 'marginBottom': '24px'})
        ]),
        
        # Main content row
        html.Div([
            # Left column: Timeline plot
            html.Div([
                dcc.Graph(
                    id="timeline-plot",
                    figure=fig,
                    style={'height': '1000px'},
                    config={'displayModeBar': True, 'displaylogo': False}
                )
            ], className="chart-container", style={'flex': '2', 'marginRight': '16px'}),
            
            # Right column: Patient context and additional metrics
            html.Div([
                side_panel,
                html.Div([
                    html.H4("Device Performance", style={'color': '#000000', 'marginBottom': '16px'}),
                    html.Div([
                        html.Div([
                            html.P(f"{mean_suction:.2f}", className="metric-value", style={'fontSize': '1.5rem'}),
                            html.P("Mean Suction", className="metric-label")
                        ], style={'textAlign': 'center', 'flex': '1'}),
                        
                        html.Div([
                            html.P(f"{apnea_events}", className="metric-value", style={'fontSize': '1.5rem'}),
                            html.P("Apnea Events", className="metric-label")
                        ], style={'textAlign': 'center', 'flex': '1'})
                    ], style={'display': 'flex', 'gap': '16px'})
                ], className="metric-card", style={'marginTop': '16px'})
            ], style={'flex': '1'})
        ], style={'display': 'flex', 'marginBottom': '24px'}),
        
        # Bottom row: Detailed analysis
        html.Div([
            html.Div([
                html.H4("Treatment Effectiveness", style={'color': '#000000', 'marginBottom': '16px'}),
                html.Div([
                    html.Div([
                        html.P(f"{ahi_without_device:.1f}/hr", className="metric-value", style={'fontSize': '1.5rem', 'color': '#ef4444'}),
                        html.P("Baseline AHI", className="metric-label")
                    ], style={'textAlign': 'center', 'flex': '1'}),
                    
                    html.Div([
                        html.P(f"{((ahi_without_device - ahi_with_device) / ahi_without_device * 100):.1f}%", 
                               className="metric-value", style={'fontSize': '1.5rem', 'color': '#10b981'}),
                        html.P("Improvement", className="metric-label")
                    ], style={'textAlign': 'center', 'flex': '1'}),
                    
                    html.Div([
                        html.P("Good" if ahi_with_device < 5 and suction_stability > 0.8 else "Needs Review", 
                               className="metric-value", 
                               style={'fontSize': '1.5rem', 
                                      'color': '#10b981' if ahi_with_device < 5 and suction_stability > 0.8 else '#f59e0b'}),
                        html.P("Assessment", className="metric-label")
                    ], style={'textAlign': 'center', 'flex': '1'})
                ], style={'display': 'flex', 'gap': '16px'})
            ], className="metric-card", style={'flex': '1', 'marginRight': '16px'}),
            
            html.Div([
                html.H4("Recommendations", style={'color': '#000000', 'marginBottom': '16px'}),
                html.Div([
                    html.P("• Continue current settings" if ahi_with_device < 5 else "• Adjust suction pressure", 
                           style={'color': '#333333', 'margin': '8px 0'}),
                    html.P("• Monitor comfort levels" if suction_stability > 0.8 else "• Check device fit", 
                           style={'color': '#333333', 'margin': '8px 0'}),
                    html.P("• Schedule follow-up in 1 month", 
                           style={'color': '#333333', 'margin': '8px 0'})
                ])
            ], className="metric-card", style={'flex': '1'})
        ], style={'display': 'flex'})
    ])

def create_timeline_plot(patient_data, patient_id):
    """Create comprehensive sleep study timeline plot in Noxturnal style with rich hover data"""
    
    # Create sleep stages data (simplified)
    sleep_stages = []
    for i, row in patient_data.iterrows():
        if i < 10:  # First 10 minutes - wake
            sleep_stages.append('Wake')
        elif i < 20:  # Next 10 minutes - NREM
            sleep_stages.append('NREM')
        elif i < 30:  # Next 10 minutes - REM
            sleep_stages.append('REM')
        elif i < 40:  # Next 10 minutes - NREM
            sleep_stages.append('NREM')
        elif i < 50:  # Next 10 minutes - REM
            sleep_stages.append('REM')
        else:  # Rest - NREM
            sleep_stages.append('NREM')
    
    patient_data = patient_data.copy()
    patient_data['SleepStage'] = sleep_stages
    
    # Create subplots with more signals like Noxturnal
    fig = make_subplots(
        rows=8, cols=1,
        subplot_titles=('Sleep Stages', 'Apneas/Hypopneas', 'RIP Phase (Effort)', 
                       'Desaturation (SpO₂)', 'Pulse Rate', 'Snoring dB', 'Movement', 'Events'),
        vertical_spacing=0.08,
        specs=[[{"secondary_y": False}],
               [{"secondary_y": False}],
               [{"secondary_y": False}],
               [{"secondary_y": False}],
               [{"secondary_y": False}],
               [{"secondary_y": False}],
               [{"secondary_y": False}],
               [{"secondary_y": False}]]
    )
    
    # Update subplot titles font
    fig.update_annotations(font=dict(family='Space Mono', size=12, color='#374151'))
    
    # 1. Sleep Stages (horizontal bars like Noxturnal)
    sleep_colors = {'Wake': '#ffd700', 'NREM': '#87ceeb', 'REM': '#ffb6c1'}
    for stage in ['Wake', 'NREM', 'REM']:
        stage_data = patient_data[patient_data['SleepStage'] == stage]
        if len(stage_data) > 0:
            fig.add_trace(
                go.Scatter(
                    x=stage_data['Time'], 
                    y=[1] * len(stage_data),
                    mode='markers',
                    marker=dict(size=20, color=sleep_colors[stage], symbol='square'),
                    name=stage,
                    showlegend=False,
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                'Time: %{x}min | Comfort: %{customdata[0]}/10<br>' +
                                '%{customdata[1]}<br>' +
                                '<extra></extra>',
                    customdata=stage_data[['ComfortScore', 'ContextualInfo']].values
                ),
                row=1, col=1
            )
    
    # Update layout with Space Mono typography for graphs
    fig.update_layout(
        title=dict(
            text=f"Signal Overview - Patient {patient_id} (Version 2)",
            font=dict(color='#000000', size=20, family='Space Mono', weight=400),
            x=0.5
        ),
        height=1000,
        showlegend=False,
        hovermode='x unified',
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff',
        font=dict(color='#374151', family='Space Mono'),
        margin=dict(l=120, r=50, t=100, b=80),
        hoverlabel=dict(
            bgcolor='rgba(255, 255, 255, 0.95)',
            bordercolor='#e2e8f0',
            font=dict(size=12, family="Space Mono, monospace", color='#374151'),
            namelength=-1
        )
    )
    
    return fig

def create_side_panel(patient_survey, patient_id):
    """Create side panel with patient survey context"""
    if patient_survey is None:
        return html.Div([
            html.H3(f"Patient {patient_id} Context", style={'color': '#1e293b', 'marginBottom': '20px'}),
            html.P("No survey data available", style={'color': '#64748b'})
        ], className="metric-card")
    
    # Determine status colors based on scores
    comfort_color = '#059669' if patient_survey['ComfortScore'] >= 7 else '#d97706' if patient_survey['ComfortScore'] >= 5 else '#dc2626'
    compliance_color = '#059669' if 'Excellent' in patient_survey['Compliance'] else '#d97706' if 'Good' in patient_survey['Compliance'] else '#dc2626'
    
    return html.Div([
        html.H3(f"Patient {patient_id} - {patient_survey['Gender']}, {patient_survey['Age']}y", 
                style={'color': '#1e293b', 'marginBottom': '20px'}),
        
        # Demographics
        html.H4("Demographics", style={'color': '#374151', 'fontSize': '16px', 'marginBottom': '12px'}),
        html.Div([
            html.P(f"Age: {patient_survey['Age']} years", style={'margin': '6px 0', 'color': '#64748b'}),
            html.P(f"BMI: {patient_survey['BMI']}", style={'margin': '6px 0', 'color': '#64748b'}),
            html.P(f"Gender: {patient_survey['Gender']}", style={'margin': '6px 0', 'color': '#64748b'})
        ], style={'marginBottom': '16px'}),
        
        html.Hr(style={'borderColor': '#e2e8f0', 'margin': '16px 0'}),
        
        # Enhanced version marker
        html.Div([
            html.H4("Version 2 Features", style={'color': '#2563eb', 'fontSize': '16px', 'marginBottom': '12px'}),
            html.P("✨ Enhanced Analytics", style={'margin': '6px 0', 'color': '#2563eb'}),
            html.P("🔍 Advanced Monitoring", style={'margin': '6px 0', 'color': '#2563eb'}),
            html.P("📊 Improved Visualizations", style={'margin': '6px 0', 'color': '#2563eb'})
        ], style={'marginBottom': '16px'}),
        
        html.Hr(style={'borderColor': '#e2e8f0', 'margin': '16px 0'}),
        
        # Post-treatment
        html.H4("Post-Treatment", style={'color': '#374151', 'fontSize': '16px', 'marginBottom': '12px'}),
        html.Div([
            html.P(f"Comfort Score: {patient_survey['ComfortScore']}/10", 
                   style={'margin': '6px 0', 'fontWeight': 'bold', 'fontSize': '1.1rem', 'color': comfort_color}),
            html.P(f"Compliance: {patient_survey['Compliance']}", 
                   style={'margin': '6px 0', 'color': compliance_color, 'fontWeight': 'bold'}),
            html.P(f"Feedback: {patient_survey['PostTreatmentFeedback']}", 
                   style={'margin': '6px 0', 'color': '#64748b', 'fontSize': '14px', 'lineHeight': '1.4'})
        ], style={'marginBottom': '16px'})
        
    ], className="metric-card", style={'height': '800px', 'overflowY': 'auto'})

def create_patient_details_page(patient_id):
    """Create detailed patient information page"""
    return html.Div([
        html.H2(f"Patient Details - Version 2 - Patient {patient_id}", className="section-title"),
        html.Div([
            html.H3("Enhanced Patient Information", style={'marginBottom': '20px'}),
            html.P("This is the Version 2 enhanced patient details page", className="body-text"),
            html.P("Additional features and improvements coming soon", className="body-text")
        ], className="metric-card")
    ])

def create_sleep_analysis_page(patient_id):
    """Create sleep analysis page"""
    return html.Div([
        html.H2(f"Sleep Analysis - Version 2 - Patient {patient_id}", className="section-title"),
        html.Div([
            html.H3("Enhanced Sleep Analysis", style={'marginBottom': '20px'}),
            html.P("This is the Version 2 sleep analysis page", className="body-text")
        ], className="metric-card")
    ])

def create_device_settings_page(patient_id):
    """Create device settings page"""
    return html.Div([
        html.H2(f"Device Settings - Version 2 - Patient {patient_id}", className="section-title"),
        html.Div([
            html.H3("Enhanced Device Management", style={'marginBottom': '20px'}),
            html.P("This is the Version 2 device settings page", className="body-text")
        ], className="metric-card")
    ])

def create_reports_page(patient_id):
    """Create reports page"""
    return html.Div([
        html.H2(f"Reports - Version 2 - Patient {patient_id}", className="section-title"),
        html.Div([
            html.H3("Enhanced Reporting", style={'marginBottom': '20px'}),
            html.P("This is the Version 2 reports page", className="body-text")
        ], className="metric-card")
    ])

def create_settings_page(patient_id):
    """Create settings page"""
    return html.Div([
        html.H2("Dashboard Settings - Version 2", className="section-title"),
        html.Div([
            html.H3("Enhanced Settings", style={'marginBottom': '20px'}),
            html.P("This is the Version 2 settings page", className="body-text")
        ], className="metric-card")
    ])

if __name__ == "__main__":
    app.run(debug=True, port=8054)  # Prototype 4 server
