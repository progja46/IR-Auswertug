import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

st.set_page_config(layout="wide")

# === Hilfsfunktionen ===

def load_data(file):
    try:
        df = pd.read_csv(file, skiprows=1, sep=';', names=["Wavenumber_cm_1", "Transmission"])
        df = df.dropna()
        df["Wavenumber_cm_1"] = pd.to_numeric(df["Wavenumber_cm_1"], errors='coerce')
        df["Transmission"] = pd.to_numeric(df["Transmission"], errors='coerce')
        return df.dropna()
    except Exception as e:
        st.error(f"Error loading file {file.name}: {e}")
        return None

def get_negative_peaks(x, y, prominence=0.1, top_n=10):
    peaks_data = []
    peaks_neg, props_neg = find_peaks(-y, prominence=prominence)
    top_neg = sorted(zip(peaks_neg, props_neg["prominences"]), key=lambda t: t[1], reverse=True)[:top_n]
    for i, _ in top_neg:
        peaks_data.append(("Negativ", int(x[i]), round(y[i], 2)))
    return peaks_data

def annotate_negative_peaks(ax, x, y, prominence=0.1, top_n=10, color='blue'):
    peaks = get_negative_peaks(x, y, prominence, top_n)
    for typ, wn, intensity in peaks:
        ax.plot(wn, intensity, marker='o', color=color)
        ax.text(wn, intensity, f"{wn}", fontsize=9, ha='center', va='top', color=color)

def plot_spectra(dfs, settings, show_peaks, x_range, font_size, legend_pos, line_width):
    fig, ax = plt.subplots(figsize=(10, 6))
    start_x, end_x = x_range

    for name, df in dfs.items():
        if df is None or df.empty:
            continue
        df_range = df[(df["Wavenumber_cm_1"] <= start_x) & (df["Wavenumber_cm_1"] >= end_x)]
        if df_range.empty:
            st.warning(f"No data in range {end_x} to {start_x} for `{name}`")
            continue
        color = settings[name]["color"]
        label = settings[name]["label"]
        ax.plot(df_range["Wavenumber_cm_1"], df_range["Transmission"], label=label, color=color, linewidth=line_width)
        if show_peaks:
            annotate_negative_peaks(ax, df_range["Wavenumber_cm_1"].values, df_range["Transmission"].values,
                                    top_n=10, color=color)
        st.write(f"Plotted {len(df_range)} points for `{name}`.")

    ax.invert_xaxis()
    ax.set_xlabel("Wavenumber (cm⁻¹)", fontsize=font_size)
    ax.set_ylabel("Transmission (%T)", fontsize=font_size)
    ax.tick_params(axis='both', which='major', labelsize=font_size)
    ax.legend(loc=legend_pos, fontsize=font_size)
    plt.tight_layout()
    return fig

# === Streamlit App ===

st.title("IR Spectrum Viewer")

uploaded_files = st.file_uploader(
    "Drag & drop CSV files here",
    accept_multiple_files=True,
    type=["csv"]
)

if uploaded_files:
    dfs = {}
    default_colors = ["#2066a8", "#8ecida", "#cdelec", "#ededed", "#f6d6c2", "#d47264", "#ae282c"]
    settings = {}

    for i, file in enumerate(uploaded_files):
        df = load_data(file)
        if df is not None:
            dfs[file.name] = df
            settings[file.name] = {
                "color": default_colors[i % len(default_colors)],
                "label": file.name
            }

    st.subheader("Spectrum Display Range")
    col1, col2 = st.columns(2)
    with col1:
        start_x = st.number_input("Start Wavenumber (cm⁻¹)", min_value=600, max_value=4000, value=4000, step=1)
    with col2:
        end_x = st.number_input("End Wavenumber (cm⁻¹)", min_value=600, max_value=4000, value=600, step=1)

    st.subheader("Spectrum Settings")
    st.markdown("Adjust color and label for each uploaded spectrum:")

    for name in settings:
        col1, col2, col3 = st.columns([2, 1, 3])
        with col1:
            st.text(name)
        with col2:
            color = st.color_picker(f"Color for `{name}`", value=settings[name]["color"], key=f"color_{name}")
            settings[name]["color"] = color
        with col3:
            label = st.text_input(f"Label for `{name}`", value=settings[name]["label"], key=f"label_{name}")
            settings[name]["label"] = label

    show_peaks = st.checkbox("Show Negative Peaks (minima)", value=True)

    font_size = st.slider("Font size for labels & legend", min_value=8, max_value=24, value=12)
    line_width = st.slider("Line width", min_value=1, max_value=5, value=2)
    legend_pos = st.selectbox("Legend position",
                              options=["best", "upper right", "upper left", "lower left", "lower right", "right",
                                       "center left", "center right", "lower center", "upper center", "center"],
                              index=0)

    st.subheader("Spectrum Preview")

    fig = plot_spectra(dfs, settings, show_peaks, (start_x, end_x), font_size, legend_pos, line_width)
    st.pyplot(fig)

    # Download peaks table
    if show_peaks:
        all_peaks = []
        for name, df in dfs.items():
            peaks = get_negative_peaks(df["Wavenumber_cm_1"].values, df["Transmission"].values, prominence=0.1, top_n=10)
            for typ, wn, intensity in peaks:
                all_peaks.append([name, typ, wn, intensity])

        if all_peaks:
            peaks_df = pd.DataFrame(all_peaks, columns=["Spectrum", "Peak Type", "Wavenumber (cm⁻¹)", "Intensity (%T)"])
            csv = peaks_df.to_csv(index=False).encode('utf-8')
            st.download_button(label="Download Negative Peaks Table as CSV", data=csv, file_name="negative_peaks.csv", mime="text/csv")

    # Download plot image
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    st.download_button("Download Spectrum Plot as PNG", data=buf, file_name="spectrum_plot.png", mime="image/png")

else:
    st.info("Please upload at least one CSV file to get started.")
