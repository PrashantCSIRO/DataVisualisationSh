import streamlit as st

# Title
st.title("Brine Data Visualiser")

# Sidebar Instructions
with st.sidebar:
    st.header("📋 Instructions")
    st.markdown("""
    **How to Use This App:**
    - Upload a spreadsheet in `.csv`, `.xls`, or `.xlsx` format.
    - Select the desired sheet containing the water quality data.
    - Follow the on-screen options to process and visualise the data.

    **Data Formatting Requirements:**
    - The **first column** must contain the **parameter names** (e.g., pH, Turbidity, etc.).
    - The **first row** must contain the **sampling dates** in a consistent format (e.g., DD/MM/YYYY or MM/YYYY).
    - Any value with a '<' sign (e.g., '<0.1') will be converted to **0**.
    - Blank cells must be left empty (they will automatically be filled as **0**).
    - Multiple sheets are supported — make sure to select the correct sheet after upload.

    **Features Available:**
    - Clean and standardise your uploaded dataset.
    - View scatter plots between two water quality parameters.
    - View time series trends for one or more parameters.
    - View parameter ratios over time.

    **Output Tips:**
    - Sampling dates are reformatted to **MM-YY** style for clarity.
    - Duplicate dates or parameters are automatically merged using the **mean** value.

    """)

    st.info("Please ensure your data matches the required structure before uploading.")

# Optional: Expandable detailed help
with st.expander("🔎 Need more detailed help? Click here"):
    st.markdown("""
    ### Sample Spreadsheet Layout:

    | Parameter    | 01/01/2022 | 01/02/2022 | 01/03/2022 |
    |--------------|------------|------------|------------|
    | pH           | 7.2        | 7.0        | 7.1        |
    | Turbidity    | <0.5       | 0.6        |            |
    | Conductivity | 450        | 460        | 455        |

    - After upload, the app will clean, transpose, and visualise your data.
    - You can select parameters for scatter plots and time series graphs easily.

    """)

# Continue with your main app logic below...

import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

# Function to load spreadsheet
def load_spreadsheet(uploaded_file):
    if uploaded_file.name.endswith('.csv'):
        return {'Sheet1': pd.read_csv(uploaded_file)}
    else:
        return pd.read_excel(uploaded_file, sheet_name=None)

# Function to clean the data
def clean_data(df):
    # Replace '<' followed by a number with 0
    df = df.applymap(lambda x: 0 if isinstance(x, str) and x.strip().startswith('<') else x)

    # Replace blanks (NaN) with 0
    df = df.fillna(0)

    # Assume first column is parameter name
    parameters = df.iloc[:, 0]

    # Assume first row is dates
    dates = df.columns[1:]

    # Create a new DataFrame with cleaned structure
    cleaned_df = pd.DataFrame(df.iloc[:, 1:].values, columns=dates)
    cleaned_df.insert(0, 'Parameter', parameters)

    # Handle duplicate dates
    if cleaned_df.columns.duplicated().any():
        duplicated_dates = cleaned_df.columns[1:][cleaned_df.columns.duplicated()[1:]]
        for date in duplicated_dates.unique():
            cols = cleaned_df.filter(regex=f"^{date}$").columns
            cleaned_df[date] = cleaned_df[cols].mean(axis=1)
            cleaned_df = cleaned_df.drop(columns=[col for col in cols if col != date])

    # Handle duplicate parameters
    if cleaned_df['Parameter'].duplicated().any():
        duplicated_params = cleaned_df['Parameter'][cleaned_df['Parameter'].duplicated()].unique()
        for param in duplicated_params:
            param_rows = cleaned_df[cleaned_df['Parameter'] == param]
            mean_values = param_rows.iloc[:, 1:].mean(axis=0)
            first_index = param_rows.index[0]
            cleaned_df.loc[first_index, cleaned_df.columns[1:]] = mean_values
            cleaned_df = cleaned_df.drop(param_rows.index[1:])

    # Reset index for neatness
    cleaned_df = cleaned_df.reset_index(drop=True)
    
    return cleaned_df

# Scatter plot function
def scatter_plot(data, param_x, param_y):
    # Ensure data contains numeric values for the selected parameters
    data = data[[param_x, param_y]].dropna().astype(float)
    fig = px.scatter(
        data_frame=data,
        x=param_x,
        y=param_y,
        labels={'x': param_x, 'y': param_y},
        title=f'Scatter Plot of {param_x} vs {param_y}'
    )
    st.plotly_chart(fig)

# Time series line chart function
def time_series_plot(data, selected_params):
    # Ensure Sampling Date is properly formatted as datetime
    data = data.melt(id_vars='Parameter', var_name='Sampling Date', value_name='Value')
    data['Sampling Date'] = pd.to_datetime(data['Sampling Date'], errors='coerce')
    data = data.dropna(subset=['Sampling Date', 'Value'])
    fig = px.line(
        data_frame=data[data['Parameter'].isin(selected_params)],
        x='Sampling Date',
        y='Value',
        color='Parameter',
        labels={'Value': 'Parameter Value', 'Sampling Date': 'Sampling Date'},
        title='Time Series of Parameters over Time'
    )
    fig.update_xaxes(
        tickformat="%b %Y",  # Display months and years
        dtick="M1"          # Set tick interval to monthly
    )
    fig.update_layout(legend_title_text='Parameters')
    st.plotly_chart(fig)

# Ratio plot function
def ratio_plot(data, numerator, denominator):
    # Ensure data contains numeric values for the selected parameters
    ratio_data = data.set_index('Parameter').T
    ratio_data = ratio_data[[numerator, denominator]].dropna().astype(float)
    ratio = ratio_data[numerator] / ratio_data[denominator].replace(0, np.nan)
    fig = px.line(
        x=ratio.index,
        y=ratio.values,
        labels={'x': 'Sampling Date', 'y': f'{numerator} / {denominator} Ratio'},
        title=f'Ratio of {numerator} to {denominator} over Time'
    )
    fig.update_xaxes(
        tickformat="%b %Y",  # Display months and years
        dtick="M1"          # Set tick interval to monthly
    )
    st.plotly_chart(fig)

# Streamlit app layout
st.title("Water Quality Data Visualiser")

uploaded_file = st.file_uploader("Upload your Spreadsheet (.csv, .xls, .xlsx)", type=['csv', 'xls', 'xlsx'])

if uploaded_file:
    sheets = load_spreadsheet(uploaded_file)
    sheet_name = st.selectbox("Select Sheet to Load", list(sheets.keys()))
    df = sheets[sheet_name]
    
    st.subheader("Raw Data Preview")
    st.dataframe(df)

    cleaned_df = clean_data(df)

    st.subheader("Cleaned Data Preview")
    st.dataframe(cleaned_df)

    st.markdown("---")
    st.header("Visualisations")

    parameters = cleaned_df['Parameter'].unique().tolist()

    # Scatter Plot
    st.subheader("Scatter Plot Between Two Parameters")
    param_x = st.selectbox("Select X-axis Parameter", parameters, key='scatter_x')
    param_y = st.selectbox("Select Y-axis Parameter", parameters, key='scatter_y')
    scatter_data = cleaned_df.set_index('Parameter').T
    scatter_plot(scatter_data, param_x, param_y)

    # Time Series Line Chart
    st.subheader("Time Series Line Chart")
    selected_params = st.multiselect("Select Parameters for Time Series Plot", parameters, key='time_series_params')
    if selected_params:
        ts_data = cleaned_df[cleaned_df['Parameter'].isin(selected_params)]
        time_series_plot(ts_data, selected_params)

    # Ratio Plot
    st.subheader("Ratio Plot Between Two Parameters")
    numerator = st.selectbox("Select Numerator Parameter", parameters, key='ratio_num')
    denominator = st.selectbox("Select Denominator Parameter", parameters, key='ratio_den')
    ratio_data = cleaned_df
    ratio_plot(ratio_data, numerator, denominator)

