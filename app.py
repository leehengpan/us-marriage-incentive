import streamlit as st
import pandas as pd
from policyengine_us.variables.household.demographic.geographic.state_code import StateCode
import table
import heatmap

# Streamlit heading and description
st.header("Marriage Incentive Calculator")
st.write("This application evaluates marriage penalties and bonuses of couples, based on state and individual employment income")
st.markdown("This application utilizes the [`policyengine-us` Python package](https://github.com/policyengine/policyengine-us).")

# Streamlit inputs for state code, head income, and spouse income
statecodes = [s.value for s in StateCode]
US_TERRITORIES = {
    "GU": "Guam", "MP": "Northern Mariana Islands", "PW": "Palau", 
    "PR": "Puerto Rico", "VI": "Virgin Islands", "AA": "Armed Forces Americas", 
    "AE": "Armed Forces Africa/Canada/Europe/Middle East", "AP": "Armed Forces Pacific"
}
options = [value for value in statecodes if value not in US_TERRITORIES]
state_code = st.selectbox("State Code", options)
head_employment_income = st.number_input("Head Employment Income", min_value=0, step=10000, value=0)
spouse_employment_income = st.number_input("Spouse Employment Income", min_value=0, step=10000, value=0)
head_disability = st.checkbox("Head is disabled")
spouse_disability = st.checkbox("Spouse is disabled")
num_children = st.number_input("Number of Children", 0)
children_ages = {}
disability_status = {"head": head_disability, "spouse": spouse_disability}

for num in range(1, num_children + 1):
    children_ages[num] = st.number_input(f"Child {num} Age", 0)
    disability_status[f'child_{num}'] = st.checkbox(f"Child {num} is disabled")

submit = st.button("Calculate")

# Helper functions
def get_combined_data(programs, index, tab_name):
    categories = list(programs[0][index].keys())
    married_values = list(programs[0][index].values())
    head_values = list(programs[1][index].values())
    spouse_values = list(programs[2][index].values())
    separate_values = [x + y for x, y in zip(head_values, spouse_values)]
    
    return table.create_table_data(categories, married_values, separate_values, tab_name)

def display_dataframe(df, tab_name):
    st.markdown("### Current situation:")
    st.dataframe(df.drop(columns=["Tab"]), hide_index=True)
    fig = heatmap.create_heatmap_chart(state_code, children_ages, tab_name, disability_status)
    st.plotly_chart(fig, use_container_width=True)

# Main logic
if submit:
    programs = table.get_categorized_programs(state_code, head_employment_income, spouse_employment_income, children_ages, disability_status)

    programs_list = ["Net income", "Benefits", "Refundable tax credits", "Taxes before refundable credits"]
    married_programs = programs[0][:-3]
    head_separate = programs[1][:-3]
    spouse_separate = programs[2][:-3]
    separate = [x + y for x, y in zip(head_separate, spouse_separate)]

    total_data = table.create_table_data(programs_list, married_programs, separate, "Summary", filter_zeros=False)
    
    benefits_data = get_combined_data(programs, -2, "Benefits Breakdown")
    credits_data = get_combined_data(programs, -1, "Refundable Credits")
    taxes_data = get_combined_data(programs, -3, "Taxes before Refundable Credits")

    all_data = pd.concat([total_data, benefits_data, credits_data, taxes_data])

    tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Benefits Breakdown", "Refundable Credits", "Taxes before Refundable Credits"])
    
    with tab1:
        display_dataframe(all_data[all_data["Tab"] == "Summary"], "Net Income")
    with tab2:
        display_dataframe(all_data[all_data["Tab"] == "Benefits Breakdown"], "Benefits")
    with tab3:
        display_dataframe(all_data[all_data["Tab"] == "Refundable Credits"], "Refundable Tax Credits")
    with tab4:
        display_dataframe(all_data[all_data["Tab"] == "Taxes before Refundable Credits"], "Tax Before Refundable Credits")


# Add the note at the bottom
st.markdown("***")
st.markdown("*We attribute all dependents to the head of household when considering unamrried filers*")
