import streamlit as st
import pandas as pd
import math
import time
import ast

st.set_page_config(layout="centered", page_title="Pump Selection Tool")

@st.cache_data
def load_pump_data():
    try:
        df = pd.read_csv('pumps.csv')
        df['Min Head m'] = df['Head m'].apply(lambda x: ast.literal_eval(x)[0] if isinstance(x, str) and x.startswith('[') else x)
        return df
    except FileNotFoundError:
        st.error("Error: pumps.csv not found. Please make sure 'pumps.csv' is in the same directory.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading pump data: {e}")
        return pd.DataFrame()

pump_data = load_pump_data()

def calculate_pump_head(vertical_height, horizontal_distance, bends_fittings_loss, pressure_head_kgcm2, stp_capacity):
    # 1. Pressure head in meters
    pressure_head_meters = pressure_head_kgcm2 * 10

    # 2. Flow rate from STP capacity (KLD to LPS)
    flow_rate_lps = (stp_capacity * 1000) / (24 * 60 * 60)

    # 3. Friction loss due to flow rate (K is placeholder constant)
    flow_friction_loss = 0.1 * (flow_rate_lps ** 2)

    # 4. Static friction loss based on pipe length
    static_friction_loss = (vertical_height + horizontal_distance) * 0.083 * 0.8

    # 5. Total friction loss
    total_friction_loss = static_friction_loss + flow_friction_loss

    # 6. Total head
    total_head_unrounded = vertical_height + total_friction_loss + bends_fittings_loss + pressure_head_meters
    total_head = math.ceil(total_head_unrounded)

    return flow_rate_lps, flow_friction_loss, total_friction_loss, total_head, pressure_head_meters, total_head_unrounded

def draw_bar(label, value):
    bar = '█' * int(value / 2)
    return f"{label:<30}: {bar} ({value:.2f} m)"

# UI
st.title("🔧 Automated Pump Head Calculator")
st.markdown("This tool calculates the required pump head based on building parameters and **STP capacity**, and suggests suitable pump models.")

st.header("🏢 Input Building Parameters")
vertical_height = st.number_input("Vertical Height from pump suction (Meters)", min_value=0.0, value=66.0, step=0.1, format="%.2f")
horizontal_distance = st.number_input("Horizontal Distance to farthest outlet (Meters)", min_value=0.0, value=109.0, step=0.1, format="%.2f")
pipe_size_str = st.text_input("Pipe Size (reference only)", value='6" GI')
bends_fittings_loss = st.number_input("Head loss in Bends and Fittings (Meters)", min_value=0.0, value=5.0, step=0.1, format="%.2f")
pressure_head_kgcm2 = st.number_input("Required Pressure (Kg/cm²)", min_value=0.0, value=3.5, step=0.1, format="%.2f")
#stp_capacity = st.number_input("STP Capacity (KLD)", min_value=1.0, value=100.0)
# Load STP capacity from Excel file


try:
    stp_df = pd.read_excel("stp_output_summary.xlsx")
    #st.write(stp_df.columns.tolist())
    stp_options = stp_df["STP Capacity (KLD)"].dropna().unique().tolist()
    selected_capacity = st.selectbox("Select STP Capacity (KLD) from Excel", stp_options)
    stp_capacity = float(selected_capacity)
except FileNotFoundError:
    st.error("❌ 'stp_output_summary.xlsx' not found. Please generate the file first.")
    st.stop()
except Exception as e:
    st.error(f"⚠️ Failed to load STP Capacity from Excel: {e}")
    st.stop()


st.markdown("---")

if st.button("⚙️ Calculate Pump Head & Suggest Pump"):
    if pump_data.empty:
        st.error("Pump data not loaded. Please check 'pumps.csv'.")
    else:
        with st.spinner("Calculating..."):
            time.sleep(1)

            # Call method
            flow_rate_lps, flow_friction_loss, total_friction_loss, total_head, pressure_head_meters, total_head_unrounded = calculate_pump_head(
                vertical_height, horizontal_distance, bends_fittings_loss, pressure_head_kgcm2, stp_capacity
            )

            st.markdown("## ✅ Calculation Results")
            st.success(f"**Total Head Required:** {total_head} Meters")

            # Recommend Pumps
            suitable_pumps = pump_data[pump_data['Min Head m'] >= total_head].copy()
            if suitable_pumps.empty:
                st.warning("⚠️ No suitable pumps found for the calculated total head.")
            else:
                st.markdown("### ✅ Recommended Pumps:")
                recommended_display = suitable_pumps[['Model', 'Manufacturer', 'HP', 'Head m', 'Suitability']]
                recommended_display.columns = ['Pump Model', 'Manufacturer', 'Horsepower (HP)', 'Head Range (m)', 'Suitability']
                st.dataframe(recommended_display)

            # Visual Breakdown
            st.markdown("---")
            st.header("🧮 Head Component Breakdown")
            st.subheader("Flow Rate Derived:")
            st.info(f"**Flow Rate (from STP):** {flow_rate_lps:.2f} LPS")

            st.subheader("Loss Components")
            st.text(draw_bar("Vertical Height", vertical_height))
            st.text(draw_bar("Static Friction Loss", total_friction_loss - flow_friction_loss))
            st.text(draw_bar("Flow-based Friction Loss", flow_friction_loss))
            st.text(draw_bar("Bends/Fittings Loss", bends_fittings_loss))
            st.text(draw_bar("Pressure Head", pressure_head_meters))

            # Detailed breakdown
            st.markdown(
                f"""
                <details>
                <summary><strong>🔍 Detailed Calculation Steps</strong></summary>
                <ul>
                    <li>STP Capacity: {stp_capacity} KLD</li>
                    <li>Flow Rate = ({stp_capacity} × 1000) / (24 × 60 × 60) = **{flow_rate_lps:.2f} LPS**</li>
                    <li>Flow Friction Loss = 0.1 × Flow² = **{flow_friction_loss:.2f} m**</li>
                    <li>Static Friction Loss = ({vertical_height:.2f} + {horizontal_distance:.2f}) × 0.083 × 0.8 = **{(total_friction_loss - flow_friction_loss):.2f} m**</li>
                    <li>Bends/Fittings Loss = **{bends_fittings_loss:.2f} m**</li>
                    <li>Pressure Head = {pressure_head_kgcm2:.2f} Kg/cm² = **{pressure_head_meters:.2f} m**</li>
                    <li>Total Head (unrounded) = **{total_head_unrounded:.2f} m**</li>
                    <li><strong>Rounded Total Head = {total_head} m</strong></li>
                </ul>
                </details>
                """,
                unsafe_allow_html=True
            )

st.markdown("""
<style>
    .stNumberInput { font-size: 20px; }
    .stButton { font-size: 18px; padding: 8px; }
    details summary {
        cursor: pointer;
        font-size: 16px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)
