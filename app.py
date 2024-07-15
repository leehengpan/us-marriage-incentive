import streamlit as st
import pandas as pd
from policyengine_us.variables.household.demographic.geographic.state_code import StateCode
import table
import heatmap

st.header("Marriage Incentive Calculator")
st.write("This application evaluates marriage penalties and bonuses of couples, based on state and individual employment income")
st.markdown("This application utilizes the [`policyengine-us` Python package](https://github.com/policyengine/policyengine-us).")

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
children_ages = {num: st.number_input(f"Child {num} Age", 0) for num in range(1, num_children + 1)}
disability_status = {"head": head_disability, "spouse": spouse_disability}
submit = st.button("Calculate")

if submit:
    programs = table.get_categorized_programs(
        state_code, head_employment_income, spouse_employment_income, children_ages, disability_status
    )

    programs_list = ["Net income", "Benefits", "Refundable tax credits", "Taxes before refundable credits"]
    married_programs = programs[0][:-3]
    head_separate = programs[1][:-3]
    spouse_separate = programs[2][:-3]
    separate = [x + y for x, y in zip(head_separate, spouse_separate)]

    total_data = table.create_table_data(programs_list, married_programs, separate, "Summary", filter_zeros=False)

    benefits_categories = list(programs[0][-2].keys())
    benefits_married = list(programs[0][-2].values())
    benefits_head = list(programs[1][-2].values())
    benefits_spouse = list(programs[2][-2].values())
    benefits_separate = [x + y for x, y in zip(benefits_head, benefits_spouse)]

    benefits_data = table.create_table_data(
        benefits_categories, benefits_married, benefits_separate, "Benefits Breakdown"
    )

    credits_categories = list(programs[0][-1].keys())
    credits_married = list(programs[0][-1].values())
    credits_head = list(programs[1][-1].values())
    credits_spouse = list(programs[2][-1].values())
    credits_separate = [x + y for x, y in zip(credits_head, credits_spouse)]

    credits_data = table.create_table_data(
        credits_categories, credits_married, credits_separate, "Refundable Credits"
    )

    taxes_categories = list(programs[0][-3].keys())
    taxes_married = list(programs[0][-3].values())
    taxes_head = list(programs[1][-3].values())
    taxes_spouse = list(programs[2][-3].values())
    taxes_separate = [x + y for x, y in zip(taxes_head, taxes_spouse)]

    taxes_data = table.create_table_data(
        taxes_categories, taxes_married, taxes_separate, "Taxes before Refundable Credits"
    )

    all_data = pd.concat([total_data, benefits_data, credits_data, taxes_data])

    tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Benefits Breakdown", "Refundable Credits", "Taxes before Refundable Credits"])
    with tab1:
        st.dataframe(all_data[all_data["Tab"] == "Summary"].drop(columns=["Tab"]), hide_index=True)
    with tab2:
        st.dataframe(all_data[all_data["Tab"] == "Benefits Breakdown"].drop(columns=["Tab"]), hide_index=True)
    with tab3:
        st.dataframe(all_data[all_data["Tab"] == "Refundable Credits"].drop(columns=["Tab"]), hide_index=True)
    with tab4:
        st.dataframe(all_data[all_data["Tab"] == "Taxes before Refundable Credits"].drop(columns=["Tab"]), hide_index=True)

    with tab1:
        fig = heatmap.create_heatmap_chart(state_code, children_ages, "Net Income", disability_status)
        st.plotly_chart(fig, use_container_width=True)
    with tab2:
        fig = heatmap.create_heatmap_chart(state_code, children_ages, "Benefits", disability_status)
        st.plotly_chart(fig, use_container_width=True)
    with tab3:
        fig = heatmap.create_heatmap_chart(state_code, children_ages, "Refundable Tax Credits", disability_status)
        st.plotly_chart(fig, use_container_width=True)
    with tab4:
        fig = heatmap.create_heatmap_chart(state_code, children_ages, "Tax Before Refundable Credits", disability_status)
        st.plotly_chart(fig, use_container_width=True)
