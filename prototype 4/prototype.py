import dash
from dash import dcc, html, Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import re

# Example: load signals + survey data
# New CSV columns: time, NasalFlow_cmH2O, SpO2_pct, Activity_gps, PosAngle_deg, AudioVolume_dB, cRIP_Flow
signals = pd.read_csv("signals.csv")  # Full resolution for windowed view
signals_fullnight = pd.read_csv("signals_fullnight.csv")  # Downsampled for full night view
surveys = pd.read_csv("surveys.csv")  # columns: PatientID, Age, BMI, ComfortScore, Comments

# Add PatientID to both signal datasets (assuming this is Patient 101)
signals['PatientID'] = 101
signals_fullnight['PatientID'] = 101

# Use the actual column names from the new CSV
# No need to rename - we'll use them directly in the visualization

# Parse N008N1SASReport.csv for real data
def parse_nox_report(file_path):
    """Parse N008N1SASReport CSV to extract key metrics"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Extract metrics using regex (account for leading quotes in CSV)
        ahi_match = re.search(r'"?Apneas \+ Hypopneas \(AH\):\s+(\d+\.?\d*)\s*/h', content)
        odi_match = re.search(r'"?Oxygen Desaturation Index \(ODI\):\s+(\d+\.?\d*)\s*/h', content)
        avg_spo2_match = re.search(r'"?Average SpO2:\s+(\d+\.?\d*)\s*%', content)
        min_spo2_match = re.search(r'"?Minimum SpO2:\s+(\d+\.?\d*)\s*%', content)
        sleep_time_match = re.search(r'"?Total Sleep Time \(TST\):\s+(\d+)h\s+(\d+)m', content)
        supine_match = re.search(r'"?Supine \(in TST\):.*?(\d+\.?\d*)\s*%', content)
        apnea_index_match = re.search(r'^"?Apneas:\s+(\d+\.?\d*)\s*/h', content, re.MULTILINE)  # Apneas per hour
        apnea_count_match = re.search(r'"?Apneas:.*?(\d+)\s*$', content, re.MULTILINE)
        arousal_match = re.search(r'"?Arousal index in TST:\s+(\d+\.?\d*)/h', content)
        
        data = {
            'ahi': float(ahi_match.group(1)) if ahi_match else 28.9,
            'odi': float(odi_match.group(1)) if odi_match else 22.6,
            'avg_spo2': float(avg_spo2_match.group(1)) if avg_spo2_match else 92.7,
            'min_spo2': float(min_spo2_match.group(1)) if min_spo2_match else 51,
            'sleep_time_hours': float(sleep_time_match.group(1)) + float(sleep_time_match.group(2))/60 if sleep_time_match else 8.5,
            'supine_pct': float(supine_match.group(1)) if supine_match else 29.1,
            'apnea_index': float(apnea_index_match.group(1)) if apnea_index_match else 16.8,  # Apneas per hour
            'apnea_count': int(apnea_count_match.group(1)) if apnea_count_match else 143,
            'arousal_index': float(arousal_match.group(1)) if arousal_match else 0
        }
        
        # Calculate desaturation events from ODI
        data['desat_events'] = int(data['odi'] * data['sleep_time_hours'])
        
        # Estimate awakenings from arousal index
        data['awakenings'] = max(1, int(data['arousal_index'] * data['sleep_time_hours'] / 10))
        
        return data
    except Exception as e:
        print(f"Error parsing Nox report: {e}")
        # Return default values
        return {
            'ahi': 28.9,
            'odi': 22.6,
            'avg_spo2': 92.7,
            'min_spo2': 51,
            'sleep_time_hours': 8.5,
            'supine_pct': 29.1,
            'apnea_index': 16.8,  # Apneas per hour
            'apnea_count': 143,
            'desat_events': 192,
            'awakenings': 6,
            'arousal_index': 0
        }

# Load Nox report data for Night 1 baseline
try:
    nox_baseline = parse_nox_report("N008N1SASReport.csv")
except Exception as e:
    print(f"Error parsing Night 1: {e}")
    nox_baseline = {
        'ahi': 28.9,
        'odi': 22.6,
        'avg_spo2': 92.7,
        'min_spo2': 51,
        'sleep_time_hours': 8.5,
        'supine_pct': 29.1,
        'apnea_index': 16.8,  # Apneas per hour
        'apnea_count': 143,
        'desat_events': 192,
        'awakenings': 6
    }

# Load Nox report data for Night 2 (CPAP)
try:
    nox_night2 = parse_nox_report("N008N2SASReport.csv")
except:
    nox_night2 = {
        'ahi': 5.2,
        'odi': 1.1,
        'avg_spo2': 95.1,
        'min_spo2': 69,
        'sleep_time_hours': 8.1,
        'supine_pct': 15.6,
        'apnea_index': 4.4,
        'apnea_count': 36,
        'desat_events': 9,
        'awakenings': 1
    }

# Load Nox report data for Night 3 (Mouthguard)
try:
    nox_night3 = parse_nox_report("N008N3SASReport.csv")
except Exception as e:
    print(f"Error parsing Night 3: {e}")
    nox_night3 = {
        'ahi': 5.5,
        'odi': 11.0,
        'avg_spo2': 92.6,
        'min_spo2': 83,
        'sleep_time_hours': 7.1,
        'supine_pct': 63.7,
        'apnea_index': 2.0,
        'apnea_count': 14,
        'desat_events': 78,
        'awakenings': 1
    }

# Create variations for different nights
def create_night_variations(baseline, night2_data, night3_data):
    """Create data for 3 nights using actual Nox report data"""
    
    # Night 1: Baseline (No Device) - use actual Nox data
    night1 = {
        'ahi': baseline['ahi'],
        'odi': baseline['odi'],
        'sleep_time': baseline['sleep_time_hours'],
        'supine': baseline['supine_pct'],
        'awakenings': baseline['awakenings'],
        'detaching': 0,  # No device
        'latch_percent': 0,
        'suction_bulb': 0,
        'suction_cup': 0
    }
    
    # Night 2: CPAP - use actual Nox data
    night2 = {
        'ahi': night2_data['ahi'],
        'odi': night2_data['odi'],
        'sleep_time': night2_data['sleep_time_hours'],
        'supine': night2_data['supine_pct'],
        'awakenings': night2_data['awakenings'],
        'detaching': 0,  # CPAP has no detaching episodes
        'latch_percent': 0,  # CPAP doesn't use latch
        'suction_bulb': 0,  # CPAP metrics
        'suction_cup': 0
    }
    
    # Night 3: Mouthguard Device - use actual Nox data with device metrics
    night3 = {
        'ahi': night3_data['ahi'],
        'odi': night3_data['odi'],
        'sleep_time': night3_data['sleep_time_hours'],
        'supine': night3_data['supine_pct'],
        'awakenings': night3_data['awakenings'],
        'detaching': 1,
        'latch_percent': 96,
        'suction_bulb': 13.8,
        'suction_cup': 9.1
    }
    
    return [night1, night2, night3]

# Generate night data based on Nox reports
nights_data_generated = create_night_variations(nox_baseline, nox_night2, nox_night3)

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
signals_fullnight_with_survey = signals_fullnight.merge(surveys, on='PatientID', how='left')

# Add comprehensive contextual information for hover tooltips
def add_contextual_info(row):
    """Add rich contextual information based on signal values and patient data"""
    context = []
    clinical_insights = []
    
    # SpO2 clinical context (using new column name)
    if row['SpO2_pct'] < 88:
        context.append("Severe desaturation - critical oxygen drop")
        clinical_insights.append("Immediate intervention may be needed")
    elif row['SpO2_pct'] < 90:
        context.append("Moderate desaturation - patient likely felt breathless")
        clinical_insights.append("Consistent with sleep apnea episodes")
    elif row['SpO2_pct'] < 95:
        context.append("Mild desaturation - may have felt tired upon waking")
        clinical_insights.append("Monitor for patterns")
    else:
        context.append("Normal oxygen levels - good respiratory function")
    
    # Flow clinical context (using new column name)
    if row['NasalFlow_cmH2O'] < 0.1:
        context.append("Complete apnea - total breathing cessation")
        clinical_insights.append("Central or obstructive apnea event")
    elif row['NasalFlow_cmH2O'] < 0.3:
        context.append("Severe hypopnea - minimal airflow")
        clinical_insights.append("Significant airway obstruction")
    elif row['NasalFlow_cmH2O'] < 0.6:
        context.append("Moderate hypopnea - reduced breathing")
        clinical_insights.append("Partial airway obstruction")
    else:
        context.append("Normal airflow - clear breathing")
    
    # Activity context (using new column name)
    if row['Activity_gps'] > 0.01:
        context.append("High activity - patient movement detected")
        clinical_insights.append("Possible awakening or position change")
    elif row['Activity_gps'] > 0.001:
        context.append("Moderate activity - restless sleep")
        clinical_insights.append("Monitor for sleep fragmentation")
    else:
        context.append("Minimal activity - stable sleep")
    
    # Comfort and compliance insights
    if row['ComfortScore'] <= 3:
        clinical_insights.append(f"Poor comfort ({row['ComfortScore']}/10) may affect compliance")
    elif row['ComfortScore'] <= 6:
        clinical_insights.append(f"Moderate comfort ({row['ComfortScore']}/10) - room for improvement")
    else:
        clinical_insights.append(f"Good comfort ({row['ComfortScore']}/10) supports treatment adherence")
    
    # BMI-related insights
    if row['BMI'] > 30:
        clinical_insights.append("Obesity may increase sleep apnea severity")
    elif row['BMI'] > 25:
        clinical_insights.append("Overweight - weight management may help")
    
    # Age-related insights
    if row['Age'] > 60:
        clinical_insights.append("Age-related increased apnea risk")
    elif row['Age'] < 40:
        clinical_insights.append("Younger patient - consider underlying causes")
    
    # Combine all insights
    all_insights = context + clinical_insights
    return " | ".join(all_insights) if all_insights else "Normal sleep patterns with good device function"

signals_with_survey['ContextualInfo'] = signals_with_survey.apply(add_contextual_info, axis=1)

# External stylesheets for medical dashboard styling
external_stylesheets = [
    'https://codepen.io/chriddyp/pen/bWLwgP.css',
    '/assets/style.css'
]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)

app.layout = html.Div([
    # Store component for navigation state
    dcc.Store(id='current-page', data='overview'),
    
    # Header Section - Manufacturing style
    html.Div([
        html.Div([
            html.H1("Sleep Apnea Patient Dashboard", 
                   style={'color': '#000000', 'margin': '0', 'fontSize': '2rem', 'fontWeight': '400', 'letterSpacing': '-0.03em', 'lineHeight': '1.1'}),
            html.P("Analysis of Patient Sleep and Device Performance", 
                  style={'color': '#666666', 'margin': '8px 0 0 0', 'fontSize': '14px', 'fontWeight': '400', 'lineHeight': '1.4'})
        ], style={'flex': '1'}),
        
        # Control Panel - Manufacturing style
        html.Div([
            html.Label("Patient ID", style={'color': '#666666', 'fontSize': '12px', 'fontWeight': '400', 'marginBottom': '4px', 'lineHeight': '1.4'}),
            dcc.Dropdown(
                id="patient-dropdown",
                options=[{"label": f"Patient {pid}", "value": pid} for pid in signals_with_survey["PatientID"].unique()],
                value=signals_with_survey["PatientID"].unique()[0],
                style={'width': '180px', 'fontSize': '14px'},
                className="patient-dropdown"
            )
        ], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'flex-end'})
    ], style={
        'display': 'flex', 
        'justifyContent': 'space-between', 
        'alignItems': 'flex-start',
        'padding': '16px 24px',
        'borderBottom': '1px solid #e2e8f0',
        'backgroundColor': '#ffffff'
    }),
    
    # Main Dashboard Content
    html.Div(id="main-content", style={'padding': '16px'})
], style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh', 'fontFamily': 'Space Mono, monospace'})

@app.callback(
    Output("main-content", "children"),
    [Input("patient-dropdown", "value")]
)
def update_dashboard(patient_id):
    if not patient_id:
        return html.Div("Please select a patient")
    
    patient_data = signals_with_survey[signals_with_survey["PatientID"] == patient_id]
    
    if len(patient_data) == 0:
        return html.Div(f"No data available for Patient {patient_id}")
    
    # Get survey data (same for all time points for this patient)
    patient_survey = patient_data.iloc[0] if len(patient_data) > 0 else None
    
    # Calculate summary metrics from Nox-based data
    mean_spo2 = nox_baseline['avg_spo2']  # Use actual Nox data
    min_spo2 = nox_baseline['min_spo2']   # Use actual Nox data
    # No suction data in new CSV - using placeholders
    mean_suction = 0.5
    suction_stability = 0.85
    
    # Use ODI from Nox report for Night 1 (baseline)
    odi_baseline = nox_baseline['odi']
    
    # Use actual apnea index (per hour) from Nox report
    apnea_index = nox_baseline['apnea_index']
    
    # Use AHI values from generated night data
    ahi_without_device = nights_data_generated[0]['ahi']  # Night 1 baseline
    ahi_cpap = nights_data_generated[1]['ahi']            # Night 2 CPAP
    ahi_with_device = nights_data_generated[2]['ahi']     # Night 3 device
    
    # Get Night 3 (device) values for delta calculations
    apnea_index_device = nox_night3['apnea_index']
    odi_device = nox_night3['odi']
    mean_spo2_device = nox_night3['avg_spo2']
    min_spo2_device = nox_night3['min_spo2']
    
    # Manufacturing-style KPI Cards
    kpi_cards = html.Div([
        # Row 1: Primary Metrics (AHI comparison with CPAP and Device, treatment efficacy, apnea events, ODI)
        html.Div([
            create_ahi_comparison_card_with_cpap("AHI (/hr)", ahi_without_device, ahi_cpap, ahi_with_device, "Apnea-Hypopnea Index"),
            create_kpi_card("Treatment Efficacy", f"{((ahi_without_device - ahi_with_device) / ahi_without_device * 100):.1f}%", "success", "Device improvement vs baseline"),
            create_delta_kpi_card("Apnea Index", apnea_index, apnea_index_device, "Apneas per hour"),
            create_delta_kpi_card("ODI", odi_baseline, odi_device, "Oxygen Desaturation Index"),
        ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(4, 1fr)', 'gap': '16px', 'marginBottom': '16px'}),
        
        # Row 2: Secondary Metrics (Mean SPO2, Nadir SPO2, suction stability, mean suction)
        html.Div([
            create_delta_kpi_card("Mean SpO₂", mean_spo2, mean_spo2_device, "Oxygen saturation average"),
            create_delta_kpi_card("Nadir SpO₂", min_spo2, min_spo2_device, "Lowest oxygen level"),
            create_kpi_card("Suction Stability", "N/A", "info", "Data pending"),
            create_kpi_card("Mean Suction", "N/A", "info", "Data pending"),
        ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(4, 1fr)', 'gap': '16px', 'marginBottom': '24px'})
    ])
    
    # Create main charts (initial load with window 0)
    timeline_chart = create_manufacturing_timeline(patient_data, patient_id, window_index=0)
    overview_charts = create_overview_charts(patient_data, patient_id)
    
    return html.Div([
        kpi_cards,
        
        # Main Content Area: Sleep & Device Panels (Left 70%) + Patient Comments (Right 28%)
        html.Div([
            # Left Side: Sleep and Device Panels
            html.Div([
                # Sleep Data Panel
                html.Div([
                    # Header row with title and night labels with conditions
                    html.Div([
                        html.Div("Sleep Data", style={
                            'color': '#374151',
                            'fontSize': '18px',
                            'fontFamily': 'Space Mono, monospace',
                            'fontWeight': '600',
                            'display': 'inline-block',
                            'width': '25%',
                            'verticalAlign': 'bottom'
                        }),
                        html.Div([
                            html.Div("Night 1", style={
                                'fontSize': '16px',
                                'fontFamily': 'Space Mono, monospace',
                                'fontWeight': '600',
                                'color': '#374151',
                                'marginBottom': '4px'
                            }),
                            html.Div("(No Device)", style={
                                'fontSize': '12px',
                                'fontFamily': 'Space Mono, monospace',
                                'fontWeight': '400',
                                'color': '#9ca3af'
                            })
                        ], style={
                            'display': 'inline-block',
                            'width': '25%',
                            'textAlign': 'center',
                            'verticalAlign': 'bottom'
                        }),
                        html.Div([
                            html.Div("Night 2", style={
                                'fontSize': '16px',
                                'fontFamily': 'Space Mono, monospace',
                                'fontWeight': '600',
                                'color': '#374151',
                                'marginBottom': '4px'
                            }),
                            html.Div("(CPAP)", style={
                                'fontSize': '12px',
                                'fontFamily': 'Space Mono, monospace',
                                'fontWeight': '400',
                                'color': '#6366f1'
                            })
                        ], style={
                            'display': 'inline-block',
                            'width': '25%',
                            'textAlign': 'center',
                            'verticalAlign': 'bottom'
                        }),
                        html.Div([
                            html.Div("Night 3", style={
                                'fontSize': '16px',
                                'fontFamily': 'Space Mono, monospace',
                                'fontWeight': '600',
                                'color': '#374151',
                                'marginBottom': '4px'
                            }),
                            html.Div("(Mouthguard)", style={
                                'fontSize': '12px',
                                'fontFamily': 'Space Mono, monospace',
                                'fontWeight': '400',
                                'color': '#10b981'
                            })
                        ], style={
                            'display': 'inline-block',
                            'width': '25%',
                            'textAlign': 'center',
                            'verticalAlign': 'bottom'
                        })
                    ], style={
                        'borderBottom': '2px solid #3b82f6',
                        'paddingBottom': '8px',
                        'marginBottom': '16px'
                    }),
                    create_sleep_display_panel(patient_data, patient_survey)
                ], style={
                    'backgroundColor': '#ffffff',
                    'borderRadius': '8px',
                    'padding': '16px',
                    'border': '1px solid #e2e8f0',
                    'marginBottom': '20px'
                }),
                
                # Device Data Panel
                html.Div([
                    # Header row with title and night label with condition
                    html.Div([
                        html.Div("Device Data", style={
                            'color': '#374151',
                            'fontSize': '18px',
                            'fontFamily': 'Space Mono, monospace',
                            'fontWeight': '600',
                            'display': 'inline-block',
                            'width': '50%',
                            'verticalAlign': 'bottom'
                        }),
                        html.Div([
                            html.Div("Night 3", style={
                                'fontSize': '16px',
                                'fontFamily': 'Space Mono, monospace',
                                'fontWeight': '600',
                                'color': '#374151',
                                'marginBottom': '4px'
                            }),
                            html.Div("(Mouthguard)", style={
                                'fontSize': '12px',
                                'fontFamily': 'Space Mono, monospace',
                                'fontWeight': '400',
                                'color': '#10b981'
                            })
                        ], style={
                            'display': 'inline-block',
                            'width': '50%',
                            'textAlign': 'center',
                            'verticalAlign': 'bottom'
                        })
                    ], style={
                        'borderBottom': '2px solid #10b981',
                        'paddingBottom': '8px',
                        'marginBottom': '16px'
                    }),
                    create_device_display_panel(patient_data, patient_survey)
                ], style={
                    'backgroundColor': '#ffffff',
                    'borderRadius': '8px',
                    'padding': '16px',
                    'border': '1px solid #e2e8f0'
                })
            ], style={
                'width': '70%',
                'display': 'inline-block',
                'verticalAlign': 'top'
            }),
            
            # Right Side: Patient Comments + AHI Criteria
            html.Div([
                # Patient Comments Panel
                html.Div([
                    html.H3("Patient Comments", style={
                        'color': '#374151',
                        'fontSize': '18px',
                        'marginBottom': '16px',
                        'fontFamily': 'Space Mono, monospace',
                        'fontWeight': '600',
                        'borderBottom': '2px solid #f59e0b',
                        'paddingBottom': '8px'
                    }),
                    create_patient_comment_display_panel(patient_survey)
                ], style={
                    'backgroundColor': '#ffffff',
                    'borderRadius': '8px',
                    'padding': '16px',
                    'border': '1px solid #e2e8f0',
                    'marginBottom': '20px'
                }),
                
                # AHI Criteria Summary Panel
                html.Div([
                    html.H4("AHI Diagnostic Criteria", style={
                        'color': '#374151',
                        'fontSize': '16px',
                        'marginBottom': '12px',
                        'fontFamily': 'Space Mono, monospace',
                        'fontWeight': '600',
                        'borderBottom': '2px solid #6366f1',
                        'paddingBottom': '6px'
                    }),
                    html.Div([
                        html.H5("3% Criteria (AASM):", style={
                            'color': '#dc2626',
                            'fontSize': '13px',
                            'marginBottom': '6px',
                            'fontFamily': 'Space Mono, monospace',
                            'fontWeight': '600'
                        }),
                        html.Ul([
                            html.Li("3% drop in blood oxygen saturation", style={'fontSize': '11px', 'fontFamily': 'Space Mono, monospace', 'marginBottom': '3px'}),
                            html.Li("More diagnoses and potential treatment denials", style={'fontSize': '11px', 'fontFamily': 'Space Mono, monospace', 'marginBottom': '3px'}),
                            html.Li("Favored by AASM for improved diagnosis", style={'fontSize': '11px', 'fontFamily': 'Space Mono, monospace', 'marginBottom': '8px'})
                        ], style={'marginLeft': '16px', 'marginBottom': '8px'}),
                        
                        html.H5("4% Criteria (CMS):", style={
                            'color': '#059669',
                            'fontSize': '13px',
                            'marginBottom': '6px',
                            'fontFamily': 'Space Mono, monospace',
                            'fontWeight': '600'
                        }),
                        html.Ul([
                            html.Li("4% drop in blood oxygen saturation", style={'fontSize': '11px', 'fontFamily': 'Space Mono, monospace', 'marginBottom': '3px'}),
                            html.Li("CMS standard with fewer diagnoses", style={'fontSize': '11px', 'fontFamily': 'Space Mono, monospace', 'marginBottom': '3px'}),
                            html.Li("Insurance coverage aligned with this definition", style={'fontSize': '11px', 'fontFamily': 'Space Mono, monospace'})
                        ], style={'marginLeft': '16px'})
                    ])
                ], style={
                    'backgroundColor': '#ffffff',
                    'borderRadius': '8px',
                    'padding': '19px',
                    'border': '1px solid #e2e8f0',
                    'fontSize': '11px'
                })
            ], style={
                'width': '28%',
                'display': 'inline-block',
                'verticalAlign': 'top',
                'marginLeft': '2%'
            })
        ], style={
            'display': 'flex',
            'gap': '0',
            'marginBottom': '20px'
        }),
        
        # Signal Timeline Chart (Full Width Below) with Navigation
        html.Div([
            html.Div([
                html.Div([
                    html.H3("Signal Timeline Analysis", style={'color': '#374151', 'fontSize': '18px', 'marginBottom': '0', 'marginRight': '16px', 'fontFamily': 'Space Mono, monospace'}),
                    html.Button('🔍 30s Windows', id='view-toggle-btn', n_clicks=0,
                               style={'padding': '8px 16px', 'fontFamily': 'Space Mono, monospace',
                                     'backgroundColor': '#10b981', 'color': 'white', 'border': 'none',
                                     'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '12px', 'fontWeight': 'bold'})
                ], style={'display': 'flex', 'alignItems': 'center'}),
                html.Div([
                    html.Button('⏮ -10 Windows', id='prev-10-window-btn', n_clicks=0, 
                               style={'padding': '8px 12px', 'marginRight': '8px', 'fontFamily': 'Space Mono, monospace', 
                                     'backgroundColor': '#6366f1', 'color': 'white', 'border': 'none', 
                                     'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '11px'}),
                    html.Button('← Previous 30s', id='prev-window-btn', n_clicks=0, 
                               style={'padding': '8px 16px', 'marginRight': '8px', 'fontFamily': 'Space Mono, monospace', 
                                     'backgroundColor': '#3b82f6', 'color': 'white', 'border': 'none', 
                                     'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '12px'}),
                    html.Span(id='window-indicator', style={'marginRight': '8px', 'fontFamily': 'Space Mono, monospace', 'fontSize': '14px', 'color': '#374151'}),
                    html.Button('Next 30s →', id='next-window-btn', n_clicks=0,
                               style={'padding': '8px 16px', 'marginRight': '8px', 'fontFamily': 'Space Mono, monospace',
                                     'backgroundColor': '#3b82f6', 'color': 'white', 'border': 'none',
                                     'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '12px'}),
                    html.Button('+10 Windows ⏭', id='next-10-window-btn', n_clicks=0,
                               style={'padding': '8px 12px', 'fontFamily': 'Space Mono, monospace',
                                     'backgroundColor': '#6366f1', 'color': 'white', 'border': 'none',
                                     'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '11px'})
                ], style={'display': 'flex', 'alignItems': 'center'}, id='navigation-controls')
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '16px'}),
            
            dcc.Store(id='current-window', data=0),  # Store for current 30-second window index
            dcc.Store(id='view-mode', data='windowed'),  # Store for view mode: 'windowed' or 'fullnight'
            
            dcc.Graph(
                id='timeline-graph',
                figure=timeline_chart,
                style={'height': '1000px'},
                config={'displayModeBar': True, 'displaylogo': False}
            )
        ], style={
            'backgroundColor': '#ffffff',
            'borderRadius': '8px',
            'padding': '20px',
            'border': '1px solid #e2e8f0'
        })
    ])

# Callback for view mode toggle
@app.callback(
    [Output('view-mode', 'data'),
     Output('view-toggle-btn', 'children'),
     Output('view-toggle-btn', 'style'),
     Output('navigation-controls', 'style')],
    [Input('view-toggle-btn', 'n_clicks')],
    [State('view-mode', 'data')]
)
def toggle_view_mode(n_clicks, current_mode):
    """Toggle between windowed and full night view"""
    if n_clicks is None or n_clicks == 0:
        # Initial state - in windowed mode, button shows what we'll switch TO
        return 'windowed', '📊 Full Night View', {
            'padding': '8px 16px', 'fontFamily': 'Space Mono, monospace',
            'backgroundColor': '#f59e0b', 'color': 'white', 'border': 'none',
            'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '12px', 'fontWeight': 'bold'
        }, {'display': 'flex', 'alignItems': 'center'}
    
    # Toggle mode
    new_mode = 'fullnight' if current_mode == 'windowed' else 'windowed'
    
    if new_mode == 'fullnight':
        # Now in full night view, button shows we can switch back to windowed
        button_text = '🔍 30s Windows'
        button_style = {
            'padding': '8px 16px', 'fontFamily': 'Space Mono, monospace',
            'backgroundColor': '#10b981', 'color': 'white', 'border': 'none',
            'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '12px', 'fontWeight': 'bold'
        }
        nav_style = {'display': 'none'}  # Hide navigation controls in full night view
    else:
        # Now in windowed view, button shows we can switch to full night
        button_text = '📊 Full Night View'
        button_style = {
            'padding': '8px 16px', 'fontFamily': 'Space Mono, monospace',
            'backgroundColor': '#f59e0b', 'color': 'white', 'border': 'none',
            'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '12px', 'fontWeight': 'bold'
        }
        nav_style = {'display': 'flex', 'alignItems': 'center'}  # Show navigation controls
    
    return new_mode, button_text, button_style, nav_style

# Callbacks for 30-second window navigation
@app.callback(
    [Output('current-window', 'data'),
     Output('window-indicator', 'children')],
    [Input('prev-window-btn', 'n_clicks'),
     Input('next-window-btn', 'n_clicks'),
     Input('prev-10-window-btn', 'n_clicks'),
     Input('next-10-window-btn', 'n_clicks'),
     Input('patient-dropdown', 'value')],
    [State('current-window', 'data')]
)
def update_window(prev_clicks, next_clicks, prev_10_clicks, next_10_clicks, patient_id, current_window):
    """Handle navigation between 30-second windows"""
    if not patient_id:
        return 0, "Window 1 (0-30s)"
    
    # Get total number of windows (each window is 30 seconds at 10Hz = 300 data points)
    patient_data = signals_with_survey[signals_with_survey["PatientID"] == patient_id]
    total_points = len(patient_data)
    points_per_window = 300  # 30 seconds at 10Hz
    max_window = (total_points // points_per_window) - 1
    
    # Determine which button was clicked
    ctx = dash.callback_context
    if not ctx.triggered:
        window = 0
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        window = current_window if current_window is not None else 0
        
        if button_id == 'next-window-btn':
            window = min(window + 1, max_window)
        elif button_id == 'prev-window-btn':
            window = max(window - 1, 0)
        elif button_id == 'next-10-window-btn':
            window = min(window + 10, max_window)
        elif button_id == 'prev-10-window-btn':
            window = max(window - 10, 0)
        elif button_id == 'patient-dropdown':
            window = 0  # Reset to first window when patient changes
    
    start_time = window * 30
    end_time = (window + 1) * 30
    indicator_text = f"Window {window + 1} ({start_time}-{end_time}s) of {max_window + 1}"
    
    return window, indicator_text

@app.callback(
    Output('timeline-graph', 'figure'),
    [Input('current-window', 'data'),
     Input('patient-dropdown', 'value'),
     Input('view-mode', 'data')]
)
def update_timeline_graph(current_window, patient_id, view_mode):
    """Update the timeline graph when window, patient, or view mode changes"""
    if not patient_id:
        return go.Figure()
    
    if view_mode == 'fullnight':
        # Use downsampled data for full night view
        patient_data = signals_fullnight_with_survey[signals_fullnight_with_survey["PatientID"] == patient_id]
        return create_fullnight_timeline(patient_data, patient_id)
    else:
        # Use full resolution data for windowed view
        patient_data = signals_with_survey[signals_with_survey["PatientID"] == patient_id]
        return create_manufacturing_timeline(patient_data, patient_id, current_window)

def create_mini_sparkline(values, color='#3b82f6', height=30, signal_type='default'):
    """Create a traditional linear sparkline using actual nightly values as data points"""
    fig = go.Figure()
    
    # Use the actual values provided as the data points
    fig.add_trace(go.Scatter(
        x=list(range(len(values))),
        y=values,
        mode='lines+markers',
        line=dict(color=color, width=2),
        marker=dict(size=4, color=color),
        showlegend=False,
        hovertemplate='Night %{x+1}: %{y}<extra></extra>'
    ))
    
    fig.update_layout(
        width=80,
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False)
    )
    
    return fig

def create_sleep_display_panel(patient_data, patient_survey):
    """Create sleep display panel organized by treatment condition per night"""
    if patient_data is None or len(patient_data) == 0:
        return html.Div("No sleep data available")
    
    # Use generated data from Nox report
    nights_data = [
        {"night": "Night 1", "condition": "No Device", **nights_data_generated[0]},
        {"night": "Night 2", "condition": "CPAP", **nights_data_generated[1]},
        {"night": "Night 3", "condition": "Mouthguard", **nights_data_generated[2]}
    ]

    return html.Div([
        # Grid with treatment conditions
        html.Div([
            # AHI Row (Main metric)
            html.Div([
                html.Div("AHI (/hr)", style={'width': '25%', 'display': 'inline-block', 'fontSize': '14px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '600', 'color': '#ef4444', 'lineHeight': '1.4'}),
                html.Div(f"{nights_data[0]['ahi']}", style={'width': '25%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '28px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#dc2626'}),
                html.Div(f"{nights_data[1]['ahi']}", style={'width': '25%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '28px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#6366f1'}),
                html.Div(f"{nights_data[2]['ahi']}", style={'width': '25%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '28px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#10b981'})
            ], style={'marginBottom': '16px', 'padding': '12px 0'}),
            
            # ODI Row (Oxygen Desaturation Index)
            html.Div([
                html.Div("ODI (/hr)", style={'width': '25%', 'display': 'inline-block', 'fontSize': '14px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '600', 'color': '#f59e0b', 'lineHeight': '1.4'}),
                html.Div(f"{nights_data[0]['odi']}", style={'width': '25%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '24px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#dc2626'}),
                html.Div(f"{nights_data[1]['odi']}", style={'width': '25%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '24px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#6366f1'}),
                html.Div(f"{nights_data[2]['odi']}", style={'width': '25%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '24px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#10b981'})
            ], style={'marginBottom': '12px', 'padding': '8px 0'}),
            
            # Sleep Time Row
            html.Div([
                html.Div("Sleep Time (h)", style={'width': '25%', 'display': 'inline-block', 'fontSize': '14px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '600', 'color': '#059669', 'lineHeight': '1.4'}),
                html.Div(f"{nights_data[0]['sleep_time']}", style={'width': '25%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '24px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#dc2626'}),
                html.Div(f"{nights_data[1]['sleep_time']}", style={'width': '25%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '24px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#6366f1'}),
                html.Div(f"{nights_data[2]['sleep_time']}", style={'width': '25%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '24px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#10b981'})
            ], style={'marginBottom': '12px', 'padding': '8px 0'}),
            
            # Supine Position Row
            html.Div([
                html.Div("Supine (%)", style={'width': '25%', 'display': 'inline-block', 'fontSize': '14px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '600', 'color': '#3b82f6', 'lineHeight': '1.4'}),
                html.Div(f"{nights_data[0]['supine']}", style={'width': '25%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '24px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#dc2626'}),
                html.Div(f"{nights_data[1]['supine']}", style={'width': '25%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '24px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#6366f1'}),
                html.Div(f"{nights_data[2]['supine']}", style={'width': '25%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '24px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#10b981'})
            ], style={'marginBottom': '12px', 'padding': '8px 0'}),
            
            # Night Awakenings Row
            html.Div([
                html.Div("Awakenings", style={'width': '25%', 'display': 'inline-block', 'fontSize': '14px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '600', 'color': '#7c3aed', 'lineHeight': '1.4'}),
                html.Div(f"{nights_data[0]['awakenings']}", style={'width': '25%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '24px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#dc2626'}),
                html.Div(f"{nights_data[1]['awakenings']}", style={'width': '25%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '24px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#6366f1'}),
                html.Div(f"{nights_data[2]['awakenings']}", style={'width': '25%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '24px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#10b981'})
            ], style={'marginBottom': '20px', 'padding': '8px 0'})
        ])
    ])

def create_device_display_panel(patient_data, patient_survey):
    """Create device display panel for Night 3 Mouthguard"""
    if patient_data is None or len(patient_data) == 0:
        return html.Div("No device data available")
    
    # Use generated device data for Night 3 (Mouthguard only)
    night3_data = nights_data_generated[2]

    return html.Div([
        # Grid with treatment conditions
        html.Div([
            # Delatching Episodes Row
            html.Div([
                html.Div("Delatching Episodes", style={'width': '50%', 'display': 'inline-block', 'fontSize': '14px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '600', 'color': '#ef4444', 'lineHeight': '1.4'}),
                html.Div(f"{night3_data['detaching']}", style={'width': '50%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '24px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#10b981'})
            ], style={'marginBottom': '12px', 'padding': '8px 0'}),
            
            # Latch Percentage Row
            html.Div([
                html.Div("Latch Percentage (%)", style={'width': '50%', 'display': 'inline-block', 'fontSize': '14px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '600', 'color': '#10b981', 'lineHeight': '1.4'}),
                html.Div(f"{night3_data['latch_percent']}", style={'width': '50%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '24px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#10b981'})
            ], style={'marginBottom': '12px', 'padding': '8px 0'}),
            
            # Suction Bulb Row
            html.Div([
                html.Div("Suction Bulb (cmH2O)", style={'width': '50%', 'display': 'inline-block', 'fontSize': '14px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '600', 'color': '#3b82f6', 'lineHeight': '1.4'}),
                html.Div(f"{night3_data['suction_bulb']}", style={'width': '50%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '24px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#10b981'})
            ], style={'marginBottom': '12px', 'padding': '8px 0'}),
            
            # Suction Cup Row
            html.Div([
                html.Div("Suction Cup (cmH2O)", style={'width': '50%', 'display': 'inline-block', 'fontSize': '14px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '600', 'color': '#9333ea', 'lineHeight': '1.4'}),
                html.Div(f"{night3_data['suction_cup']}", style={'width': '50%', 'display': 'inline-block', 'textAlign': 'center', 'fontSize': '24px', 'fontFamily': 'Space Mono, monospace', 'fontWeight': '700', 'color': '#10b981'})
            ], style={'marginBottom': '20px', 'padding': '8px 0'})
        ])
    ])

def create_patient_comment_display_panel(patient_survey):
    """Create patient comment display panel with patient experience quotes"""
    if patient_survey is None or (hasattr(patient_survey, 'empty') and patient_survey.empty):
        return html.Div("No patient comments available")
    
    # Patient experience quotes with sentiment indicators
    patient_quotes = [
        {"text": "The first night was a bit uncomfortable, but I got used to it quickly.", "sentiment": "mixed"},
        {"text": "By the third night, I was sleeping much better and felt more rested in the morning.", "sentiment": "positive"},
        {"text": "My partner noticed I stopped snoring almost immediately.", "sentiment": "positive"},
        {"text": "The device is surprisingly comfortable once you find the right position.", "sentiment": "positive"},
        {"text": "I love that I can finally get a full night's sleep without waking up gasping.", "sentiment": "positive"},
        {"text": "The improvement in my energy levels during the day has been remarkable.", "sentiment": "positive"},
        {"text": "I feel claustrophobic wearing this device all night.", "sentiment": "negative"}
    ]
    
    def get_sentiment_color(sentiment):
        """Return border color based on sentiment"""
        if sentiment == "positive":
            return "#10b981"  # Green
        elif sentiment == "negative":
            return "#ef4444"  # Red
        else:  # mixed or neutral
            return "#f59e0b"  # Orange
    
    return html.Div([
        # Main patient feedback
        html.Div([
            html.H5("Patient Experience", style={'color': '#374151', 'fontSize': '14px', 'marginBottom': '12px', 'fontFamily': 'Space Mono, monospace'}),
            html.P(f'"{patient_survey["PostTreatmentFeedback"]}"', style={
                'fontStyle': 'italic',
                'color': '#1f2937',
                'fontSize': '12px',
                'lineHeight': '1.4',
                'margin': '0 0 16px 0',
                'padding': '12px',
                'backgroundColor': '#f8f9fa',
                'borderRadius': '5px',
                'borderLeft': '3px solid #3b82f6',
                'fontFamily': 'Space Mono, monospace'
            })
        ], style={'marginBottom': '16px'}),
        
        # Additional patient quotes
        html.Div([
            html.H5("Additional Comments", style={'color': '#374151', 'fontSize': '14px', 'marginBottom': '12px', 'fontFamily': 'Space Mono, monospace'}),
            html.Div([
                html.P(f'"{quote["text"]}"', style={
                    'fontStyle': 'italic',
                    'color': '#1f2937',
                    'fontSize': '11px',
                    'lineHeight': '1.4',
                    'margin': '0 0 8px 0',
                    'padding': '8px',
                    'backgroundColor': '#f8f9fa',
                    'borderRadius': '4px',
                    'borderLeft': f'3px solid {get_sentiment_color(quote["sentiment"])}',
                    'fontFamily': 'Space Mono, monospace'
                }) for quote in patient_quotes
            ])
        ])
    ])

def create_patient_info_panel(patient_survey):
    """Create patient demographics panel"""
    if patient_survey is None or (hasattr(patient_survey, 'empty') and patient_survey.empty):
        return html.Div("No patient data available")
    
    return html.Div([
        # Basic Demographics
        html.Div([
            html.Div([
                html.Strong("Demographics", style={'color': '#374151', 'fontFamily': 'Space Mono, monospace'})
            ], style={'marginBottom': '12px'}),
            
            create_info_row("Age", f"{patient_survey['Age']} years"),
            create_info_row("Gender", patient_survey['Gender']),
            create_info_row("BMI", f"{patient_survey['BMI']}"),
            create_info_row("Comfort Score", f"{patient_survey['ComfortScore']}/10"),
        ], style={'marginBottom': '20px'}),
        
        # Clinical Background
        html.Div([
            html.Div([
                html.Strong("Clinical Background", style={'color': '#374151', 'fontFamily': 'Space Mono, monospace'})
            ], style={'marginBottom': '12px'}),
            
            create_info_text("Baseline Sleep Quality", patient_survey['BaselineSleepQuality']),
            create_info_text("Pre-treatment Symptoms", patient_survey['PreTreatmentSymptoms']),
        ], style={'marginBottom': '20px'}),
        
        # Treatment Compliance
        html.Div([
            html.Div([
                html.Strong("Treatment Compliance", style={'color': '#374151', 'fontFamily': 'Space Mono, monospace'})
            ], style={'marginBottom': '12px'}),
            
            create_info_text("Compliance Level", patient_survey['Compliance']),
        ])
    ])

def create_patient_feedback_panel(patient_survey):
    """Create patient feedback quotes panel"""
    if patient_survey is None or (hasattr(patient_survey, 'empty') and patient_survey.empty):
        return html.Div("No feedback data available")
    
    # Additional quotes to show alongside the main patient feedback
    additional_quotes = [
        "The device is comfortable and I've noticed a significant improvement in my energy levels during the day.",
        "I was skeptical at first, but after two weeks I'm sleeping much better and my partner says I don't snore anymore.",
        "Easy to use and clean. The most comfortable sleep apnea solution I've tried so far.",
        "My morning headaches have completely disappeared since starting treatment with this device.",
        "I can finally get through the day without feeling drowsy. My work productivity has improved dramatically."
    ]
    
    return html.Div([
        # Patient Experience Quotes Section
        html.Div([
            html.Div([
                html.Strong("Patient Experience", style={'color': '#374151', 'fontFamily': 'Space Mono, monospace'})
            ], style={'marginBottom': '16px'}),
            
            # Main patient quote
            html.Div([
                html.P(f'"{patient_survey["PostTreatmentFeedback"]}"', style={
                    'fontStyle': 'italic',
                    'color': '#1f2937',
                    'fontSize': '12px',
                    'lineHeight': '1.4',
                    'margin': '0 0 12px 0',
                    'padding': '12px',
                    'backgroundColor': '#f8f9fa',
                    'borderRadius': '5px',
                    'borderLeft': '3px solid #d1d5db',
                    'fontFamily': 'Space Mono, monospace'
                })
            ]),
            
            # Additional patient quotes
            html.Div([
                html.P(f'"{quote}"', style={
                    'fontStyle': 'italic',
                    'color': '#1f2937',
                    'fontSize': '11px',
                    'lineHeight': '1.4',
                    'margin': '0 0 8px 0',
                    'padding': '10px',
                    'backgroundColor': '#f8f9fa',
                    'borderRadius': '5px',
                    'borderLeft': '3px solid #d1d5db',
                    'fontFamily': 'Space Mono, monospace'
                }) for quote in additional_quotes
            ])
        ])
    ])

def create_info_row(label, value):
    """Create a demographics info row"""
    return html.Div([
        html.Div([
            html.Span(label, style={
                'color': '#6b7280', 
                'fontSize': '12px',
                'fontFamily': 'Space Mono, monospace',
                'textTransform': 'uppercase',
                'letterSpacing': '0.05em'
            })
        ], style={'marginBottom': '2px'}),
        html.Div(value, style={
            'color': '#1f2937',
            'fontSize': '14px',
            'fontWeight': '600',
            'fontFamily': 'Space Mono, monospace'
        })
    ], style={'marginBottom': '12px'})

def create_info_text(label, value):
    """Create a text info section"""
    return html.Div([
        html.Div([
            html.Span(label, style={
                'color': '#6b7280', 
                'fontSize': '11px',
                'fontFamily': 'Space Mono, monospace',
                'textTransform': 'uppercase',
                'letterSpacing': '0.05em'
            })
        ], style={'marginBottom': '4px'}),
        html.P(value, style={
            'color': '#374151',
            'fontSize': '12px',
            'lineHeight': '1.4',
            'margin': '0',
            'fontFamily': 'Space Mono, monospace'
        })
    ], style={'marginBottom': '12px'})

def create_kpi_card(title, value, status, description, text_align='center'):
    """Create manufacturing-style KPI cards"""
    
    status_colors = {
        'primary': '#3b82f6',
        'success': '#10b981',
        'warning': '#f59e0b',
        'danger': '#ef4444',
        'info': '#6366f1'
    }
    
    color = status_colors.get(status, '#6b7280')
    
    return html.Div([
        html.Div([
            html.H4(title, style={
                'color': '#374151',
                'fontSize': '12px',
                'fontWeight': '400',
                'margin': '0 0 8px 0',
                'textTransform': 'uppercase',
                'letterSpacing': '0.05em',
                'fontFamily': 'Space Mono, monospace',
                'textAlign': text_align
            }),
            html.Div(value, style={
                'color': color,
                'fontSize': '24px',
                'fontWeight': '700',
                'margin': '0 0 4px 0',
                'fontFamily': 'Space Mono, monospace',
                'textAlign': text_align
            }),
            html.P(description, style={
                'color': '#6b7280',
                'fontSize': '11px',
                'margin': '0',
                'fontFamily': 'Space Mono, monospace',
                'textAlign': text_align
            })
        ])
    ], style={
        'backgroundColor': '#ffffff',
        'border': f'2px solid {color}',
        'borderRadius': '8px',
        'padding': '16px',
        'boxShadow': '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
    })

def create_delta_kpi_card(title, baseline_value, device_value, description, text_align='center'):
    """Create KPI card showing delta between baseline and device"""
    
    delta = device_value - baseline_value
    
    # Determine color based on metric type and direction of change
    # For most metrics, negative delta is good (improvement)
    if 'spo2' in title.lower() or 'mean' in title.lower():
        # For SpO2, positive delta is good
        if delta > 0:
            status = 'success'
        elif delta < -2:
            status = 'danger'
        else:
            status = 'warning'
    else:
        # For apnea index, ODI, negative delta is good (reduction)
        if delta < -5:
            status = 'success'
        elif delta > 0:
            status = 'danger'
        else:
            status = 'warning'
    
    status_colors = {
        'primary': '#3b82f6',
        'success': '#10b981',
        'warning': '#f59e0b',
        'danger': '#ef4444',
        'info': '#6366f1'
    }
    
    color = status_colors.get(status, '#6b7280')
    
    # Format delta with sign
    delta_sign = '+' if delta > 0 else ''
    delta_text = f"{delta_sign}{delta:.1f}"
    
    return html.Div([
        html.Div([
            html.H4(title, style={
                'color': '#374151',
                'fontSize': '12px',
                'fontWeight': '400',
                'margin': '0 0 8px 0',
                'textTransform': 'uppercase',
                'letterSpacing': '0.05em',
                'fontFamily': 'Space Mono, monospace',
                'textAlign': text_align
            }),
            html.Div(delta_text, style={
                'color': color,
                'fontSize': '32px',
                'fontWeight': '700',
                'margin': '0 0 4px 0',
                'fontFamily': 'Space Mono, monospace',
                'textAlign': text_align
            }),
            html.P("Change from Baseline to Device", style={
                'color': '#9ca3af',
                'fontSize': '9px',
                'margin': '0 0 4px 0',
                'fontFamily': 'Space Mono, monospace',
                'textAlign': text_align,
                'fontStyle': 'italic'
            }),
            html.P(description, style={
                'color': '#6b7280',
                'fontSize': '11px',
                'margin': '0',
                'fontFamily': 'Space Mono, monospace',
                'textAlign': text_align
            })
        ])
    ], style={
        'backgroundColor': '#ffffff',
        'border': f'2px solid {color}',
        'borderRadius': '8px',
        'padding': '16px',
        'boxShadow': '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
    })

def create_ahi_comparison_card_with_cpap(title, baseline_value, cpap_value, device_value, description):
    """Create AHI card that shows three-column comparison with actual values"""
    
    # Determine status based on device value
    if device_value < 5:
        status = 'success'
    elif device_value < 15:
        status = 'warning'
    else:
        status = 'danger'
    
    status_colors = {
        'primary': '#3b82f6',
        'success': '#10b981',
        'warning': '#f59e0b',
        'danger': '#ef4444',
        'info': '#6366f1'
    }
    
    color = status_colors.get(status, '#6b7280')
    
    return html.Div([
        html.H4(title, style={
            'color': '#374151',
            'fontSize': '12px',
            'fontWeight': '400',
            'margin': '0 0 8px 0',
            'textTransform': 'uppercase',
            'letterSpacing': '0.05em',
            'fontFamily': 'Space Mono, monospace'
        }),
        html.Div([
            # Baseline column
            html.Div([
                html.P("Baseline", style={'fontSize': '10px', 'color': '#6b7280', 'margin': '0', 'fontFamily': 'Space Mono, monospace'}),
                html.P(f"{baseline_value:.1f}", style={'fontSize': '20px', 'color': '#ef4444', 'fontWeight': '700', 'margin': '4px 0', 'fontFamily': 'Space Mono, monospace'})
            ], style={'width': '33.33%', 'display': 'inline-block', 'textAlign': 'center'}),
            # CPAP column (Night 2)
            html.Div([
                html.P("CPAP", style={'fontSize': '10px', 'color': '#6b7280', 'margin': '0', 'fontFamily': 'Space Mono, monospace'}),
                html.P(f"{cpap_value:.1f}", style={'fontSize': '20px', 'color': '#6366f1', 'fontWeight': '700', 'margin': '4px 0', 'fontFamily': 'Space Mono, monospace'})
            ], style={'width': '33.33%', 'display': 'inline-block', 'textAlign': 'center'}),
            # Device column (Night 3)
            html.Div([
                html.P("Device", style={'fontSize': '10px', 'color': '#6b7280', 'margin': '0', 'fontFamily': 'Space Mono, monospace'}),
                html.P(f"{device_value:.1f}", style={'fontSize': '20px', 'color': '#10b981', 'fontWeight': '700', 'margin': '4px 0', 'fontFamily': 'Space Mono, monospace'})
            ], style={'width': '33.33%', 'display': 'inline-block', 'textAlign': 'center'})
        ], style={'margin': '8px 0'}),
        html.P(description, style={
            'color': '#6b7280',
            'fontSize': '11px',
            'margin': '8px 0 0 0',
            'fontFamily': 'Space Mono, monospace'
        })
    ], style={
        'backgroundColor': '#ffffff',
        'border': f'2px solid {color}',
        'borderRadius': '8px',
        'padding': '16px',
        'textAlign': 'center',
        'boxShadow': '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
    })

def create_ahi_comparison_static_card(title, with_device_value, without_device_value, status, description):
    """Create AHI card that always shows three-column comparison"""
    
    status_colors = {
        'primary': '#3b82f6',
        'success': '#10b981',
        'warning': '#f59e0b',
        'danger': '#ef4444',
        'info': '#6366f1'
    }
    
    color = status_colors.get(status, '#6b7280')
    cpap_value = without_device_value - ((without_device_value - with_device_value) * 0.6)
    
    return html.Div([
        html.H4(title, style={
            'color': '#374151',
            'fontSize': '12px',
            'fontWeight': '400',
            'margin': '0 0 8px 0',
            'textTransform': 'uppercase',
            'letterSpacing': '0.05em',
            'fontFamily': 'Space Mono, monospace'
        }),
        html.Div([
            # Baseline column
            html.Div([
                html.P("Baseline", style={'fontSize': '10px', 'color': '#6b7280', 'margin': '0', 'fontFamily': 'Space Mono, monospace'}),
                html.P(f"{without_device_value:.1f}", style={'fontSize': '20px', 'color': '#ef4444', 'fontWeight': '700', 'margin': '4px 0', 'fontFamily': 'Space Mono, monospace'})
            ], style={'width': '33.33%', 'display': 'inline-block', 'textAlign': 'center'}),
            # CPAP column
            html.Div([
                html.P("CPAP", style={'fontSize': '10px', 'color': '#6b7280', 'margin': '0', 'fontFamily': 'Space Mono, monospace'}),
                html.P(f"{cpap_value:.1f}", style={'fontSize': '20px', 'color': '#f59e0b', 'fontWeight': '700', 'margin': '4px 0', 'fontFamily': 'Space Mono, monospace'})
            ], style={'width': '33.33%', 'display': 'inline-block', 'textAlign': 'center'}),
            # Device column
            html.Div([
                html.P("Device", style={'fontSize': '10px', 'color': '#6b7280', 'margin': '0', 'fontFamily': 'Space Mono, monospace'}),
                html.P(f"{with_device_value:.1f}", style={'fontSize': '20px', 'color': '#10b981', 'fontWeight': '700', 'margin': '4px 0', 'fontFamily': 'Space Mono, monospace'})
            ], style={'width': '33.33%', 'display': 'inline-block', 'textAlign': 'center'})
        ], style={'margin': '8px 0'}),
        html.P(description, style={
            'color': '#6b7280',
            'fontSize': '11px',
            'margin': '8px 0 0 0',
            'fontFamily': 'Space Mono, monospace'
        })
    ], style={
        'backgroundColor': '#ffffff',
        'border': f'2px solid {color}',
        'borderRadius': '8px',
        'padding': '16px',
        'textAlign': 'center',
        'boxShadow': '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
    })

def create_ahi_comparison_card(title, with_device_value, without_device_value, status, description):
    """Create special AHI card with both values and divider"""
    
    status_colors = {
        'primary': '#3b82f6',
        'success': '#10b981',
        'warning': '#f59e0b',
        'danger': '#ef4444',
        'info': '#6366f1'
    }
    
    color = status_colors.get(status, '#6b7280')
    
    return html.Div([
        html.Div([
            html.H4(title, style={
                'color': '#374151',
                'fontSize': '12px',
                'fontWeight': '400',
                'margin': '0 0 8px 0',
                'textTransform': 'uppercase',
                'letterSpacing': '0.05em',
                'fontFamily': 'Space Mono, monospace'
            }),
            # Top half - AHI with device
            html.Div([
                html.Div("With Device", style={
                    'color': '#6b7280',
                    'fontSize': '10px',
                    'fontWeight': '400',
                    'margin': '0',
                    'fontFamily': 'Space Mono, monospace'
                }),
                html.Div(f"{with_device_value:.1f}/hr", style={
                    'color': color,
                    'fontSize': '20px',
                    'fontWeight': '700',
                    'margin': '2px 0',
                    'fontFamily': 'Space Mono, monospace'
                })
            ], style={'marginBottom': '8px'}),
            
            # Divider line
            html.Hr(style={
                'margin': '8px 0',
                'border': 'none',
                'borderTop': f'1px solid {color}',
                'opacity': '0.3'
            }),
            
            # Bottom half - AHI without device (baseline)
            html.Div([
                html.Div("Baseline", style={
                    'color': '#6b7280',
                    'fontSize': '10px',
                    'fontWeight': '400',
                    'margin': '0',
                    'fontFamily': 'Space Mono, monospace'
                }),
                html.Div(f"{without_device_value:.1f}/hr", style={
                    'color': '#9ca3af',
                    'fontSize': '16px',
                    'fontWeight': '600',
                    'margin': '2px 0 4px 0',
                    'fontFamily': 'Space Mono, monospace'
                })
            ]),
            
            html.P(description, style={
                'color': '#6b7280',
                'fontSize': '11px',
                'margin': '4px 0 0 0',
                'fontFamily': 'Space Mono, monospace'
            })
        ])
    ], style={
        'backgroundColor': '#ffffff',
        'border': f'2px solid {color}',
        'borderRadius': '8px',
        'padding': '16px',
        'textAlign': 'center',
        'boxShadow': '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
    })

def create_manufacturing_timeline(patient_data, patient_id, window_index=0):
    """Create 30-second windowed timeline with 6 signals from Nox CSV data
    
    Signals: Sleep Position, Activity, Flow, SpO2, cRIP Flow, Audio Volume
    """
    
    # Extract 30-second window (300 data points at 10Hz)
    points_per_window = 300
    start_idx = window_index * points_per_window
    end_idx = start_idx + points_per_window
    
    # Get windowed data
    windowed_data = patient_data.iloc[start_idx:end_idx]
    
    if len(windowed_data) == 0:
        return go.Figure()  # Return empty figure if no data
    
    fig = make_subplots(
        rows=6, cols=1,
        subplot_titles=('Sleep Position', 'Activity (g/s)', 'Flow (cmH₂O)', 'SpO₂ (%)', 'cRIP Flow', 'Audio Volume (dB)'),
        vertical_spacing=0.05,
        shared_xaxes=True,
        row_heights=[0.16, 0.16, 0.17, 0.17, 0.17, 0.17]
    )
    
    # Use actual time data from the CSV file
    time_seconds = windowed_data['time'].values
    
    # Helper function to map position angle to category
    def position_angle_to_category(angle):
        """Map position angle to sleep position category"""
        if -45 <= angle <= 45:
            return 'Supine'
        elif 45 < angle <= 135:
            return 'Right'
        elif -135 <= angle < -45:
            return 'Left'
        else:
            return 'Prone'
    
    # 1. Sleep Position - map angle to categorical
    position_angles = windowed_data['PosAngle_deg'].values
    position_categories = [position_angle_to_category(angle) for angle in position_angles]
    position_numeric = [{'Supine': 2, 'Left': 1, 'Right': 3, 'Prone': 4}[cat] for cat in position_categories]
    
    fig.add_trace(go.Scatter(
        x=time_seconds, y=position_numeric,
        mode='lines',
        line=dict(color='#8B4513', width=2),
        name='Sleep Position',
        showlegend=False,
        hovertemplate='Position: %{customdata}<br>Time: %{x:.1f}s<extra></extra>',
        customdata=position_categories
    ), row=1, col=1)
    
    # 2. Activity (g/s)
    activity_data = windowed_data['Activity_gps'].values
    
    fig.add_trace(go.Scatter(
        x=time_seconds, y=activity_data,
        mode='lines',
        line=dict(color='#4B0082', width=1),
        name='Activity',
        showlegend=False,
        hovertemplate='Activity: %{y:.6f} g/s<br>Time: %{x:.1f}s<extra></extra>'
    ), row=2, col=1)
    
    # 3. Flow (cmH₂O)
    flow_data = windowed_data['NasalFlow_cmH2O'].values
    
    fig.add_trace(go.Scatter(
        x=time_seconds, y=flow_data,
        mode='lines',
        line=dict(color='#009900', width=1),
        name='Flow',
        showlegend=False,
        hovertemplate='Flow: %{y:.3f} cmH₂O<br>Time: %{x:.1f}s<extra></extra>'
    ), row=3, col=1)
    
    # 4. SpO₂ (%)
    spo2_data = windowed_data['SpO2_pct'].values
    # Clip to reasonable range
    spo2_data = np.clip(spo2_data, 70, 100)
    
    fig.add_trace(go.Scatter(
        x=time_seconds, y=spo2_data,
        mode='lines',
        line=dict(color='#0066CC', width=1),
        name='SpO₂',
        showlegend=False,
        hovertemplate='SpO₂: %{y:.1f}%<br>Time: %{x:.1f}s<extra></extra>'
    ), row=4, col=1)
    
    # Add clinical reference lines for SpO2
    fig.add_hline(y=90, line_dash="dot", line_color="#FF4444", line_width=1, row=4, col=1)
    fig.add_hline(y=95, line_dash="dot", line_color="#FFA500", line_width=1, row=4, col=1)
    
    # 5. cRIP Flow
    crip_flow_data = windowed_data['cRIP_Flow'].values
    
    fig.add_trace(go.Scatter(
        x=time_seconds, y=crip_flow_data,
        mode='lines',
        line=dict(color='#FF9900', width=1),
        name='cRIP Flow',
        showlegend=False,
        hovertemplate='cRIP Flow: %{y:.6f}<br>Time: %{x:.1f}s<extra></extra>'
    ), row=5, col=1)
    
    # 6. Audio Volume (dB)
    audio_data = windowed_data['AudioVolume_dB'].values
    
    fig.add_trace(go.Scatter(
        x=time_seconds, y=audio_data,
        mode='lines',
        line=dict(color='#9900CC', width=1),
        name='Audio Volume',
        showlegend=False,
        hovertemplate='Audio: %{y:.1f} dB<br>Time: %{x:.1f}s<extra></extra>'
    ), row=6, col=1)
    
    # Update layout for medical appearance
    start_time = time_seconds[0] if len(time_seconds) > 0 else 0
    end_time = time_seconds[-1] if len(time_seconds) > 0 else 30
    fig.update_layout(
        title=dict(
            text=f"Patient {patient_id} - Window {window_index + 1} ({start_time:.1f}s - {end_time:.1f}s) - {len(windowed_data)} data points",
            x=0.02,
            y=0.98,
            font=dict(size=16, family='Space Mono, monospace', color='#374151')
        ),
        height=1000,
        plot_bgcolor='#f8f9fa',
        paper_bgcolor='#ffffff',
        margin=dict(l=80, r=20, t=60, b=40),
        font=dict(family='Space Mono, monospace', size=9),
        hoverlabel=dict(
            bgcolor='#ffffff',
            bordercolor='#000000',
            font=dict(family='Space Mono, monospace', size=11, color='#000000'),
            align='left'
        )
    )
    
    # Update x-axes (show time in seconds)
    fig.update_xaxes(
        title_text="Time (seconds)",
        showgrid=True,
        gridwidth=1,
        gridcolor='#e5e7eb',
        showline=True,
        linewidth=1,
        linecolor='#d1d5db',
        dtick=5,  # Major tick every 5 seconds
        minor=dict(dtick=1, showgrid=True, gridcolor='#f3f4f6'),
        row=6, col=1
    )
    
    # Update y-axes for each track with appropriate ranges
    y_configs = [
        {'title': 'Position', 'range': [0.5, 4.5], 'dtick': 1, 'tickvals': [1, 2, 3, 4], 'ticktext': ['Left', 'Supine', 'Right', 'Prone']},
        {'title': 'Activity (g/s)', 'range': None, 'dtick': None},  # Auto-scale
        {'title': 'Flow (cmH₂O)', 'range': None, 'dtick': None},  # Auto-scale
        {'title': 'SpO₂ (%)', 'range': [70, 100], 'dtick': 10},
        {'title': 'cRIP Flow', 'range': None, 'dtick': None},  # Auto-scale
        {'title': 'Audio (dB)', 'range': None, 'dtick': None}  # Auto-scale
    ]
    
    for i, config in enumerate(y_configs, 1):
        update_args = {
            'title_text': config['title'],
            'showgrid': True,
            'gridwidth': 1,
            'gridcolor': '#e5e7eb',
            'showline': True,
            'linewidth': 1,
            'linecolor': '#d1d5db',
            'side': 'left',
            'row': i,
            'col': 1
        }
        
        # Only add range and dtick if they're not None
        if config['range'] is not None:
            update_args['range'] = config['range']
        if config['dtick'] is not None:
            update_args['dtick'] = config['dtick']
        
        # Add tick customization if specified
        if 'tickvals' in config:
            update_args['tickvals'] = config['tickvals']
            update_args['ticktext'] = config['ticktext']
        
        fig.update_yaxes(**update_args)
    
    return fig

def create_fullnight_timeline(patient_data, patient_id):
    """Create full night (8.5 hour) timeline view using downsampled data
    
    Displays all 6 signals across the entire night in a single view
    Optimized for 1920px width display
    """
    
    if len(patient_data) == 0:
        return go.Figure()
    
    fig = make_subplots(
        rows=6, cols=1,
        subplot_titles=('Sleep Position', 'Activity (g/s)', 'Flow (cmH₂O)', 'SpO₂ (%)', 'cRIP Flow', 'Audio Volume (dB)'),
        vertical_spacing=0.05,
        shared_xaxes=True,
        row_heights=[0.16, 0.16, 0.17, 0.17, 0.17, 0.17]
    )
    
    # Use time data in hours for better readability
    time_hours = patient_data['time'].values / 3600.0
    
    # Helper function to map position angle to category
    def position_angle_to_category(angle):
        """Map position angle to sleep position category"""
        if -45 <= angle <= 45:
            return 'Supine'
        elif 45 < angle <= 135:
            return 'Right'
        elif -135 <= angle < -45:
            return 'Left'
        else:
            return 'Prone'
    
    # 1. Sleep Position
    position_angles = patient_data['PosAngle_deg'].values
    position_categories = [position_angle_to_category(angle) for angle in position_angles]
    position_numeric = [{'Supine': 2, 'Left': 1, 'Right': 3, 'Prone': 4}[cat] for cat in position_categories]
    
    fig.add_trace(go.Scatter(
        x=time_hours, y=position_numeric,
        mode='lines',
        line=dict(color='#8B4513', width=1),
        name='Sleep Position',
        showlegend=False,
        hovertemplate='Position: %{customdata}<br>Time: %{x:.2f}h<extra></extra>',
        customdata=position_categories
    ), row=1, col=1)
    
    # 2. Activity (g/s)
    activity_data = patient_data['Activity_gps'].values
    
    fig.add_trace(go.Scatter(
        x=time_hours, y=activity_data,
        mode='lines',
        line=dict(color='#4B0082', width=0.5),
        name='Activity',
        showlegend=False,
        hovertemplate='Activity: %{y:.6f} g/s<br>Time: %{x:.2f}h<extra></extra>'
    ), row=2, col=1)
    
    # 3. Flow (cmH₂O)
    flow_data = patient_data['NasalFlow_cmH2O'].values
    
    fig.add_trace(go.Scatter(
        x=time_hours, y=flow_data,
        mode='lines',
        line=dict(color='#009900', width=0.5),
        name='Flow',
        showlegend=False,
        hovertemplate='Flow: %{y:.3f} cmH₂O<br>Time: %{x:.2f}h<extra></extra>'
    ), row=3, col=1)
    
    # 4. SpO₂ (%) - Most important signal, slightly thicker line
    spo2_data = patient_data['SpO2_pct'].values
    spo2_data = np.clip(spo2_data, 70, 100)
    
    fig.add_trace(go.Scatter(
        x=time_hours, y=spo2_data,
        mode='lines',
        line=dict(color='#0066CC', width=1),
        name='SpO₂',
        showlegend=False,
        hovertemplate='SpO₂: %{y:.1f}%<br>Time: %{x:.2f}h<extra></extra>'
    ), row=4, col=1)
    
    # Add clinical reference lines for SpO2
    fig.add_hline(y=90, line_dash="dot", line_color="#FF4444", line_width=1, row=4, col=1)
    fig.add_hline(y=95, line_dash="dot", line_color="#FFA500", line_width=1, row=4, col=1)
    
    # 5. cRIP Flow
    crip_flow_data = patient_data['cRIP_Flow'].values
    
    fig.add_trace(go.Scatter(
        x=time_hours, y=crip_flow_data,
        mode='lines',
        line=dict(color='#FF9900', width=0.5),
        name='cRIP Flow',
        showlegend=False,
        hovertemplate='cRIP Flow: %{y:.6f}<br>Time: %{x:.2f}h<extra></extra>'
    ), row=5, col=1)
    
    # 6. Audio Volume (dB)
    audio_data = patient_data['AudioVolume_dB'].values
    
    fig.add_trace(go.Scatter(
        x=time_hours, y=audio_data,
        mode='lines',
        line=dict(color='#9900CC', width=0.5),
        name='Audio Volume',
        showlegend=False,
        hovertemplate='Audio: %{y:.1f} dB<br>Time: %{x:.2f}h<extra></extra>'
    ), row=6, col=1)
    
    # Update layout
    duration_hours = time_hours[-1] if len(time_hours) > 0 else 8.5
    fig.update_layout(
        title=dict(
            text=f"Patient {patient_id} - Full Night View ({duration_hours:.1f} hours) - {len(patient_data)} data points",
            x=0.02,
            y=0.98,
            font=dict(size=16, family='Space Mono, monospace', color='#374151')
        ),
        height=1000,
        plot_bgcolor='#f8f9fa',
        paper_bgcolor='#ffffff',
        margin=dict(l=80, r=20, t=60, b=40),
        font=dict(family='Space Mono, monospace', size=9),
        hoverlabel=dict(
            bgcolor='#ffffff',
            bordercolor='#000000',
            font=dict(family='Space Mono, monospace', size=11, color='#000000'),
            align='left'
        )
    )
    
    # Update x-axes (show time in hours)
    fig.update_xaxes(
        title_text="Time (hours from sleep onset)",
        showgrid=True,
        gridwidth=1,
        gridcolor='#e5e7eb',
        showline=True,
        linewidth=1,
        linecolor='#d1d5db',
        dtick=1,  # Major tick every hour
        minor=dict(dtick=0.5, showgrid=True, gridcolor='#f3f4f6'),
        row=6, col=1
    )
    
    # Update y-axes for each track
    y_configs = [
        {'title': 'Position', 'range': [0.5, 4.5], 'dtick': 1, 'tickvals': [1, 2, 3, 4], 'ticktext': ['Left', 'Supine', 'Right', 'Prone']},
        {'title': 'Activity (g/s)', 'range': None, 'dtick': None},
        {'title': 'Flow (cmH₂O)', 'range': None, 'dtick': None},
        {'title': 'SpO₂ (%)', 'range': [70, 100], 'dtick': 10},
        {'title': 'cRIP Flow', 'range': None, 'dtick': None},
        {'title': 'Audio (dB)', 'range': None, 'dtick': None}
    ]
    
    for i, config in enumerate(y_configs, 1):
        update_args = {
            'title_text': config['title'],
            'showgrid': True,
            'gridwidth': 1,
            'gridcolor': '#e5e7eb',
            'showline': True,
            'linewidth': 1,
            'linecolor': '#d1d5db',
            'side': 'left',
            'row': i,
            'col': 1
        }
        
        if config['range'] is not None:
            update_args['range'] = config['range']
        if config['dtick'] is not None:
            update_args['dtick'] = config['dtick']
        
        if 'tickvals' in config:
            update_args['tickvals'] = config['tickvals']
            update_args['ticktext'] = config['ticktext']
        
        fig.update_yaxes(**update_args)
    
    return fig

def create_overview_charts(patient_data, patient_id):
    """Create overview charts in manufacturing style with integrated qualitative data"""
    
    # Create rich hover data for overview charts
    def create_rich_hover_data(row):
        """Create comprehensive hover information combining quantitative and qualitative data"""
        # Return as list in specific order for Plotly customdata access
        hover_data = [
            row['BaselineSleepQuality'],    # index 0
            row['SideEffects'],             # index 1
            row['Compliance']               # index 2
        ]
        return hover_data
    
    # Apply rich hover data to each row
    hover_data_list = patient_data.apply(create_rich_hover_data, axis=1).tolist()
    
    # Distribution chart
    spo2_dist = go.Figure()
    spo2_dist.add_trace(
        go.Histogram(
            x=patient_data['SpO2_pct'],
            nbinsx=20,
            marker_color='#3b82f6',
            opacity=0.7,
            name='SpO₂ Distribution'
        )
    )
    
    spo2_dist.update_layout(
        title='SpO₂ Distribution',
        xaxis_title='SpO₂ (%)',
        yaxis_title='Frequency',
        font=dict(family='Space Mono', color='#374151'),
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff',
        margin=dict(l=40, r=40, t=40, b=40),
        hoverlabel=dict(
            bgcolor='#ffffff',
            bordercolor='#000000',
            font=dict(family='Space Mono, monospace', size=12, color='#000000'),
            align='left'
        )
    )
    
    # Correlation scatter with integrated qualitative context
    correlation_fig = go.Figure()
    correlation_fig.add_trace(
        go.Scatter(
            x=patient_data['NasalFlow_cmH2O'],
            y=patient_data['SpO2_pct'],
            mode='markers',
            marker=dict(
                size=12,
                color=patient_data['Activity_gps'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(
                    title=dict(text="Activity (g/s)", font=dict(family='Space Mono')),
                    tickfont=dict(family='Space Mono')
                ),
                opacity=0.8
            ),
            name='Flow vs SpO₂',
            customdata=hover_data_list,
            hovertemplate='<b>Flow vs SpO2 Correlation</b><br>' +
                         'Flow: %{x:.3f} cmH₂O<br>' +
                         'SpO2: %{y:.1f}%<br>' +
                         'Suction: %{marker.color:.2f}<br>' +
                         '<extra></extra>'
        )
    )
    
    correlation_fig.update_layout(
        title='Airflow vs SpO₂ (colored by Suction)',
        xaxis_title='Airflow',
        yaxis_title='SpO₂ (%)',
        font=dict(family='Space Mono', color='#374151'),
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff',
        margin=dict(l=40, r=40, t=40, b=40),
        hoverlabel=dict(
            bgcolor='#ffffff',
            bordercolor='#000000',
            font=dict(family='Space Mono, monospace', size=12, color='#000000'),
            align='left'
        )
    )
    
    return html.Div([
        html.Div([
            dcc.Graph(figure=spo2_dist, style={'height': '300px'})
        ], style={'width': '48%', 'display': 'inline-block'}),
        
        html.Div([
            dcc.Graph(figure=correlation_fig, style={'height': '300px'})
        ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '4%'})
    ])


if __name__ == "__main__":
    app.run(debug=True, port=8054)  # Prototype 4 server
