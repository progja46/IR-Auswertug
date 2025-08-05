

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from io import BytesIO
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

# === FUNCTIONS ===

def load_data_from_csv(file):
    df = pd.read_csv(file, skiprows=1, sep=';', names=["Wavenumber_cm_1", "Transmission"])
    df = df.dropna()
    df["Wavenumber_cm_1"] = pd.to_numeric(df["Wavenumber_cm_1"], errors='coerce')
    df["Transmission"] = pd.to_numeric(df["Transmission"], errors='coerce')
    return df.dropna()

def get_negative_peaks(x, y, prominence=0.1, top_n=10):
    peaks_data = []
    peaks_neg, props_neg = find_peaks(-y, prominence=prominence)
    top_neg = sorted(zip(peaks_neg, props_neg["prominences"]), key=lambda t: t[1], reverse=True)[:top_n]
    for i, _ in top_neg:
        peaks_data.append({"Wavenumber (cm⁻¹)": int(x[i]), "Transmission (%T)": round(y[i], 2)})
    return peaks_data

def plot_spectra(dfs, settings, show_peaks, x_range):
    fig, ax = plt.subplots(figsize=(10, 6))
    for i, (name, df) in enumerate(dfs.items()):
        start_x, end_x = x_range
        df_range = df[(df["Wavenumber_cm_1"] <= start_x) & (df["Wavenumber_cm_1"] >= end_x)]
        label = settings[name]["label"]
        color = settings[name]["color"]
        ax.plot(df_range["Wavenumber_cm_1"], df_range["Transmission"], label=label, color=color)
        
        if show_peaks:
            x = df_range["Wavenumber_cm_1"].values
            y = df_range["Transmission"].values
            peaks = get_negative_peaks(x, y, top_n=10)
            for peak in peaks:
                ax.plot(peak["Wavenumber (cm⁻¹)"], peak["Transmission (%T)"], 'o', color=color)
                ax.text(peak["Wavenumber (cm⁻¹)"], peak["Transmission (%T)"], str(peak["Wavenumber (cm⁻¹)"]), color=color,
                        fontsize=8, ha='center', va='top')

    ax.invert_xaxis()
    ax.set_xlabel("Wavenumber (cm⁻¹)")
    ax.set_ylabel("Transmission (%T)")
    ax.set_title("IR Spectrum")
    ax.legend()
    st.pyplot(fig)
    return fig

def export_peaks_to_excel(dfs, settings, x_range):
    wb = Workbook()
    ws = wb.active
    ws.title = "Negative Peaks"
    ws.append(["Filename", "Wavenumber (cm⁻¹)", "Transmission (%T)"])

    for name, df in dfs.items():
        df_range = df[(df["Wavenumber_cm_1"] <= x_range[0]) & (df["Wavenumber_cm_1"] >= x_range[1])]
        x = df_range["Wavenumber_cm_1"].values
        y = df_range["Transmission"].values
        peaks = get_negative_peaks(x, y)
        for peak in peaks:
            ws.append([settings[name]["label"], peak["Wavenumber (cm⁻¹)"], peak["Transmission (%T)"]])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

# === STREAMLIT UI ===

st.title("IR Spectrum Analysis App")

st.markdown("Upload your IR spectra as CSV files (semicolon-separated, with header row skipped).")

uploaded_files = st.file_uploader("Upload one or more CSV files", accept_multiple_files=True, type=["csv"])

if uploaded_files:
    st.subheader("Configure Graph Display")

    # === X-Axis Range ===
    col1, col2 = st.columns(2)
    with col1:
        start_x = st.number_input("Start Wavenumber (cm⁻¹)", value=4000, step=10)
    with col2:
        end_x = st.number_input("End Wavenumber (cm⁻¹)", value=600, step=10)

    # === Load Data ===
    dfs = {}
    default_colors = ["blue", "green", "red", "purple", "orange", "brown", "cyan", "magenta"]
    settings = {}

    for i, file in enumerate(uploaded_files):
        name = file.name
        df = load_data_from_csv(file)
        dfs[name] = df
        settings[name] = {
            "color": default_colors[i % len(default_colors)],
            "label": name.replace(".csv", "")
        }

    st.subheader("Legend Settings")
    st.markdown("Customize label and color for each spectrum")

    for name in dfs.keys():
        col1, col2, col3 = st.columns([4, 2, 4])
        with col1:
            label = st.text_input(f"Legend Label for `{name}`", value=settings[name]["label"], key=f"label_{name}")
        with col2:
            color = st.color_picker(f"Color for `{name}`", value=settings[name]["color"], key=f"color_{name}")
        with col3:
            st.markdown("")

        settings[name]["label"] = label
        settings[name]["color"] = color

    # === Peak Option ===
    show_peaks = st.checkbox("Show negative peaks (minima)", value=True)

    # === Plot Preview ===
    st.subheader("Spectrum Preview")
    fig = plot_spectra(dfs, settings, show_peaks, (start_x, end_x))

    # === Downloads ===
    st.subheader("Download Results")

    col1, col2 = st.columns(2)
    with col1:
        img_buffer = BytesIO()
        fig.savefig(img_buffer, format='png', dpi=300)
        st.download_button(
            label="Download Spectrum as PNG",
            data=img_buffer.getvalue(),
            file_name="IR_spectrum.png",
            mime="image/png"
        )

    with col2:
        if show_peaks:
            excel_file = export_peaks_to_excel(dfs, settings, (start_x, end_x))
            st.download_button(
                label="Download Peaks as Excel",
                data=excel_file,
                file_name="IR_negative_peaks.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
