import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
import io

st.set_page_config(layout="wide")

# === Farbauswahl (erweiterte Heatmap) ===
color_palette = {
    "Dark Blue": "#2066a8",
    "Med Blue": "#8ecdda",
    "Light Blue": "#cde1ec",
    "Gray": "#ededed",
    "Light Red": "#f6d6c2",
    "Med Red": "#d47264",
    "Dark Red": "#ae282c",
    "Dark Teal": "#1f6f6f",
    "Med Teal": "#54a1a1",
    "Light Teal": "#9fc8c8",
    "Soft Peach": "#fee8c8",
    "Orange Mid": "#fdbb84",
    "Strong Orange": "#e34a33",
    "Black (Default)": "#000000"
}

# === Hilfsfunktionen ===

def load_data(file):
    try:
        df = pd.read_csv(file, skiprows=1, sep=';', names=["Wavenumber_cm_1", "Transmission"])
        df = df.dropna()
        df["Wavenumber_cm_1"] = pd.to_numeric(df["Wavenumber_cm_1"], errors='coerce')
        df["Transmission"] = pd.to_numeric(df["Transmission"], errors='coerce')
        return df.dropna()
    except Exception as e:
        st.error(f"Fehler beim Laden der Datei {file.name}: {e}")
        return None

def get_negative_peaks(x, y, prominence=0.1, top_n=10):
    peaks = []
    neg_peaks, props = find_peaks(-y, prominence=prominence)
    sorted_peaks = sorted(zip(neg_peaks, props["prominences"]), key=lambda t: t[1], reverse=True)[:top_n]
    for idx, _ in sorted_peaks:
        peaks.append(("Negativ", int(x[idx]), round(y[idx], 2)))
    return peaks

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
            st.warning(f"Keine Daten im Bereich {end_x}–{start_x} für `{name}`")
            continue
        color = settings[name]["color"]
        label = settings[name]["label"]
        ax.plot(df_range["Wavenumber_cm_1"], df_range["Transmission"], label=label, color=color, linewidth=line_width)
        if show_peaks:
            annotate_negative_peaks(ax, df_range["Wavenumber_cm_1"].values, df_range["Transmission"].values, top_n=10, color=color)

    ax.invert_xaxis()
    ax.set_xlabel("Wavenumber (cm⁻¹)", fontsize=font_size)
    ax.set_ylabel("Transmission (%T)", fontsize=font_size)
    ax.tick_params(axis='both', labelsize=font_size)
    ax.legend(loc=legend_pos, fontsize=font_size)
    plt.tight_layout()
    return fig

# === Streamlit App ===

st.title("IR Spectrum Viewer")

uploaded_files = st.file_uploader("Lade eine oder mehrere CSV-Dateien hoch", type=["csv"], accept_multiple_files=True)

if uploaded_files:
    dfs = {}
    settings = {}

    for i, file in enumerate(uploaded_files):
        df = load_data(file)
        if df is not None:
            name = file.name
            dfs[name] = df
            settings[name] = {
                "color": list(color_palette.values())[i % len(color_palette)],
                "label": name
            }

    st.subheader("Anzeigeeinstellungen")
    col1, col2 = st.columns(2)
    with col1:
        start_x = st.number_input("Start-Wellenzahl (cm⁻¹)", min_value=600, max_value=4000, value=4000)
    with col2:
        end_x = st.number_input("End-Wellenzahl (cm⁻¹)", min_value=600, max_value=4000, value=600)

    show_peaks = st.checkbox("Negative Peaks anzeigen", value=True)
    font_size = st.slider("Schriftgröße", min_value=8, max_value=24, value=12)
    line_width = st.slider("Liniendicke", min_value=1, max_value=5, value=2)
    legend_pos = st.selectbox("Legendenposition", options=[
        "best", "upper right", "upper left", "lower left", "lower right",
        "right", "center left", "center right", "lower center", "upper center", "center"
    ])

    st.subheader("Einstellungen je Spektrum")

    for name in settings:
        st.markdown(f"**{name}**")
        default_color = settings[name]["color"]

        color_name = st.selectbox(
            f"Farbwahl für `{name}`",
            options=list(color_palette.keys()),
            index=list(color_palette.values()).index(default_color) if default_color in color_palette.values() else 0,
            key=f"dropdown_{name}"
        )

        selected_color = color_palette[color_name]

        custom_color = st.color_picker(
            f"Individuelle Farbe für `{name}`",
            value=selected_color,
            key=f"picker_{name}"
        )

        label = st.text_input(f"Legendenlabel für `{name}`", value=settings[name]["label"], key=f"label_{name}")

        settings[name]["color"] = custom_color
        settings[name]["label"] = label

    st.subheader("Vorschau")

    fig = plot_spectra(dfs, settings, show_peaks, (start_x, end_x), font_size, legend_pos, line_width)
    st.pyplot(fig)

    st.subheader("Angezeigte Spektren")
for name in dfs:
    st.write(f"Name: {settings[name]['label']} (Datei: {name})")
    
    st.subheader("Dateinamen für Export")
    file_base = st.text_input("Dateiname ohne Erweiterung", value="spectrum_plot")

    if show_peaks:
        all_peaks = []
        for name, df in dfs.items():
            peaks = get_negative_peaks(df["Wavenumber_cm_1"].values, df["Transmission"].values, top_n=10)
            for typ, wn, intensity in peaks:
                all_peaks.append([name, typ, wn, intensity])
        if all_peaks:
            peaks_df = pd.DataFrame(all_peaks, columns=["Spektrum", "Peak-Typ", "Wellenzahl", "Intensität"])
            csv = peaks_df.to_csv(index=False).encode('utf-8')
            st.download_button("CSV mit Peaks herunterladen", data=csv, file_name=f"{file_base}_peaks.csv", mime="text/csv")

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    st.download_button("Plot als PNG herunterladen", data=buf, file_name=f"{file_base}.png", mime="image/png")

else:
    st.info("Bitte lade mindestens eine CSV-Datei hoch.")

    st.info("Please upload at least one CSV file to get started.")




