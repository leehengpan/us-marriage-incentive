import streamlit as st
import plotly.express as px
from policyengine_us import Simulation
from policyengine_core.charts import format_fig
from policyengine_us.variables.household.demographic.geographic.state_code import (
    StateCode,
)
import numpy as np
import pandas as pd
# Create a function to get net income for the household, married or separate.

def get_net_incomes(state_code, children_ages = {}):
    # Tuple of net income for separate and married.
    net_income_married = get_net_income(
        state_code, True, children_ages
    )
    net_income_separate = get_net_income(state_code,None,children_ages)
    return net_income_married, net_income_separate

DEFAULT_AGE = 40
YEAR = "2024"

def get_programs(state_code, head_employment_income, spouse_employment_income=None, children_ages = {}):
    # Start by adding the single head.
    situation = {
        "people": {
            "you": {
                "age": {YEAR: DEFAULT_AGE},
                "employment_income": {YEAR: head_employment_income},
            }
        }
    }
    members = ["you"]
    if spouse_employment_income is not None:
        situation["people"]["your partner"] = {
            "age": {YEAR: DEFAULT_AGE},
            "employment_income": {YEAR: spouse_employment_income},
        }
        # Add your partner to members list.
        members.append("your partner")
    for key, value in children_ages.items():
        situation["people"][f"child {key}"] = {
            "age": {YEAR: value},
            "employment_income": {YEAR: 0}
        }
        # Add child to members list.
        members.append(f"child {key}")
    # Create all parent entities.
    situation["families"] = {"your family": {"members": members}}
    situation["marital_units"] = {"your marital unit": {"members": members}}
    situation["tax_units"] = {"your tax unit": {"members": members}}
    situation["spm_units"] = {"your spm_unit": {"members": members}}
    situation["households"] = {
        "your household": {"members": members, "state_name": {YEAR: state_code}}
    }
    simulation = Simulation(situation=situation)

    simulation = Simulation(situation=situation)

    #benefits breakdown
    benefits_categories = [
        "social_security",
        "ssi",
        "state_supplement",
        "co_state_supplement",
        # State child care subsidies.
        "ca_child_care_subsidies",
        "co_child_care_subsidies",
        "ca_cvrp",  # California Clean Vehicle Rebate Project.
        "ca_care",
        "ca_fera",
        "co_oap",
        "snap",
        "wic",
        "free_school_meals",
        "reduced_price_school_meals",
        "spm_unit_broadband_subsidy",
        "tanf",
        "high_efficiency_electric_home_rebate",
        "residential_efficiency_electrification_rebate",
        "unemployment_compensation",
        # Contributed.
        "basic_income",
        "spm_unit_capped_housing_subsidy",
    ]

    household_net_income = int(simulation.calculate("household_net_income", int(YEAR))[0])
    household_benefits = int(simulation.calculate("household_benefits", int(YEAR))[0])
    household_refundable_tax_credits = int(simulation.calculate("household_refundable_tax_credits", int(YEAR))[0])
    household_tax_before_refundable_credits = int(simulation.calculate("household_tax_before_refundable_credits", int(YEAR))[0])
    
    benefits_dic ={}
    for benefit in benefits_categories:
        try:
            benefit_amount = int(simulation.calculate(benefit, YEAR)[0])
        except ValueError:
            benefit_amount = 0
            
        benefits_dic[benefit]=benefit_amount

    return [household_net_income ,household_benefits ,household_refundable_tax_credits,household_tax_before_refundable_credits, benefits_dic]
def get_categorized_programs(state_code, head_employment_income, spouse_employment_income,  children_ages):
     programs_married = get_programs(state_code, head_employment_income, spouse_employment_income,  children_ages)
     programs_head = get_programs(state_code, head_employment_income, None,  children_ages)
     programs_spouse = get_programs(state_code, spouse_employment_income,None, children_ages)
     return [programs_married, programs_head, programs_spouse]

# Create a function to get net income for household
def get_net_income(state_code, spouse=None, children_ages = {}):

    
    # Start by adding the single head.
    situation = {
        "people": {
            "you": {
                "age": {YEAR: DEFAULT_AGE},
            }
        }
    }
    members = ["you"]
    if spouse is not None:
        situation["people"]["your partner"] = {
            "age": {YEAR: DEFAULT_AGE},
        }
        # Add your partner to members list.
        members.append("your partner")
    for key, value in children_ages.items():
        situation["people"][f"child {key}"] = {
            "age": {YEAR: value},
        }
        # Add child to members list.
        members.append(f"child {key}")
    # Create all parent entities.
    situation["families"] = {"your family": {"members": members}}
    situation["marital_units"] = {"your marital unit": {"members": members}}
    situation["tax_units"] = {"your tax unit": {"members": members}}
    situation["spm_units"] = {"your spm_unit": {"members": members}}
    situation["households"] = {
        "your household": {"members": members, "state_name": {YEAR: state_code}}
    }
    situation["axes"]= [
        [
        {
            "name": "employment_income",
            "count": 64,
            "min": 0,
            "max": 80000,
            "period": YEAR
        }
        ]
    ]
  

    simulation = Simulation(situation=situation)

    return simulation.calculate("household_net_income", int(YEAR))

#Streamlit heading and description
header = st.header("Marriage Incentive Calculator")  
header_description = st.write("This application evaluates marriage penalties and bonuses of couples, based on state and individual employment income")
repo_link = st.markdown("This application utilizes <a href='https://github.com/PolicyEngine/us-marriage-incentive'>the policyengine API</a>", unsafe_allow_html=True)  


# Create Streamlit inputs for state code, head income, and spouse income.
statecodes = [s.value for s in StateCode]
us_territories = {
    "GU" : "Guam", 
    "MP" : "Northern Mariana Islands",
    "PW" : "Palau",
    "PR" : "Puerto Rico",
    "VI" : "Virgin Islands",
    "AA" :"Armed Forces Americas (Except Canada)",
    "AE" : "Armed Forces Africa/Canada/Europe/Middle East",
    "AP" : "Armed Forces Pacific"
}
options = [value for value in statecodes if value not in us_territories]
state_code = st.selectbox("State Code", options)
head_employment_income = st.number_input("Head Employment Income", step=20000, value=0)
spouse_employment_income = st.number_input("Spouse Employment Income", step=10000, value=0)
num_children = st.number_input("Number of Children", 0)
children_ages = {}
for num in range(1,num_children + 1):
    children_ages[num] = st.number_input(f"Child {num} Age", 0)
#submit button
submit = st.button("Calculate")
# Get net incomes.
if submit:
    programs = get_categorized_programs(state_code, head_employment_income, spouse_employment_income,  children_ages)
    
    # benefits breakdowns
    benefits_categories = programs[0][-1].keys()
    benefits_married = programs[0][-1].values()
    benefits_head = programs[1][-1].values()
    benefits_spouse = programs[2][-1].values()
    benefits_separate = [x + y for x, y in zip(benefits_head, benefits_spouse)]

    # to-do update benefits_married and benefits_separate to keep only the non zero values in either list

    benefits_delta = [x - y for x, y in zip(benefits_married, benefits_separate)]
    benefits_delta_percent = [(x - y) / x if x != 0 else 0 for x, y in zip(benefits_married, benefits_separate)]

    # format benefits breakdowns
    formatted_benefits_married = list(map(lambda x: "${:,}".format(round(x)), benefits_married))
    formatted_benefits_separate = list(map(lambda x: "${:,}".format(round(x)), benefits_separate))
    formatted_benefits_delta = list(map(lambda x: "${:,}".format(round(x)), benefits_delta))
    formatted_benefits_delta_percent = list(map(lambda x: "{:.1%}".format(x), benefits_delta_percent))

    # married programs
    married_programs = programs[0][:-1] # we exclude the last element which is the dictionary of benefits breakdown 
    formatted_married_programs = list(map(lambda x: "${:,}".format(round(x)), married_programs))
    
    # separate programs
    head_separate = programs[1][:-1] # we exclude the last element which is the dictionary of benefits breakdown 
    spouse_separate = programs[2][:-1] # we exclude the last element which is the dictionary of benefits breakdown 
    separate = [x + y for x, y in zip(head_separate, spouse_separate)]
    formatted_separate = list(map(lambda x: "${:,}".format(round(x)), separate))
    
    # delta
    delta = [x - y for x, y in zip(married_programs, separate)]
    delta_percent = [(x - y) / x if x != 0 else 0 for x, y in zip(married_programs, separate)]
    formatted_delta = list(map(lambda x: "${:,}".format(round(x)), delta))
    formatted_delta_percent = list(map(lambda x: "{:.1%}".format(x), delta_percent))

    programs = ["Net Income", "Benefits", "Refundable tax credits", "Taxes before refundable credits"]


    # Determine marriage penalty or bonus, and extent in dollars and percentage.
    marriage_bonus = married_programs[0] - separate[0]
    marriage_bonus_percent = marriage_bonus / married_programs[0]
    def summarize_marriage_bonus(marriage_bonus):
        # Create a string to summarize the marriage bonus or penalty.
        return (
            f"If you file separately, your combined net income will be ${abs(marriage_bonus):,.2f} "
            f"{'less' if marriage_bonus > 0 else 'more'} "
            f"({abs(marriage_bonus_percent):.1%}) than if you file together."
        )


    if marriage_bonus > 0:
        st.write("You face a marriage BONUS.")
    elif marriage_bonus < 0:
        st.write("You face a marriage PENALTY.")
    else:
        st.write("You face no marriage penalty or bonus.")

    st.write(summarize_marriage_bonus(marriage_bonus))

    # Formatting for visual display
    # Sample data for main table
    table_data = {
        'Program': programs,
        'Not Married': formatted_separate,
        'Married': formatted_married_programs,
        'Delta': formatted_delta,
        'Delta Percentage': formatted_delta_percent
    }

    # Benefits breakdown table
    benefits_table = {
        'Program': benefits_categories,
        'Not Married': formatted_benefits_separate,
        'Married': formatted_benefits_married,
        'Delta': formatted_benefits_delta,
        'Delta Percentage': formatted_benefits_delta_percent
        
    }
    benefits_df = pd.DataFrame(benefits_table)
    filtered_benefits_df = benefits_df[(benefits_df['Not Married'] != "$0") | (benefits_df['Married'] != "$0")]
    
    # Display the tables in Streamlit
    if not filtered_benefits_df.empty: # if we have benefits
        tab1, tab2 = st.tabs(["Summary", "Benefits Breakdown"])
        with tab1:
            st.dataframe(table_data, hide_index=True)

        with tab2:
            st.dataframe(filtered_benefits_df, hide_index=True)

    else: # if we don't have benefits, display just the main table
        st.dataframe(table_data, hide_index=True)
    
    def calculate_bonus():
        married_incomes , separate_incomes = get_net_incomes(state_code, children_ages)
        bonus_penalties = [x - y for x, y in zip(married_incomes.tolist(), separate_incomes.tolist())]
        array = np.array(bonus_penalties)
        nested_lists = np.reshape(array, (8, 8))
        return nested_lists

        
    def get_chart():
    # Function to calculate the input data (replace with your actual data calculation)
        # Set numerical values for x and y axes
        x_values = [10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000]
        y_values = [10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000]

        # Display loading spinner while calculating data
        with st.spinner("Calculating Heatmap... May take 90 seconds"):
            # Calculate data (replace with your actual data calculation)
            data = calculate_bonus()

        abs_max = max(abs(min(map(min, data))), abs(max(map(max, data))))
        z_min = -abs_max
        z_max = abs_max
        color_scale = [
                (0, '#616161'), 
                (0.5, '#FFFFFF'),  
                (1, '#2C6496')  
                ]
        # Display the chart once data calculation is complete
        fig = px.imshow(data,
                        labels=dict(x="Head Employment Income", y="Spouse Employment Income", color="Net Income Change"),
                        x=x_values,
                        y=y_values,
                        zmin=z_min,
                        zmax=z_max,
                        color_continuous_scale=color_scale,
                        origin='lower'
                    )

        fig.update_xaxes(side="bottom")
        fig.update_layout(
            xaxis=dict(
                tickmode='array',
                tickvals=[10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000],
                ticktext=["{}k".format(int(val/1000)) for val in [10000,20000, 30000,40000,50000, 60000, 70000, 80000]],
                showgrid=True,
                zeroline=False,
                title=dict(text='Head Employment Income', standoff=15),
            ),
            yaxis=dict(
                tickmode='array',
                tickvals=[10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000],
                ticktext=["{}k".format(int(val/1000)) for val in [10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000]],
                showgrid=True,
                zeroline=False,
                title=dict(text='Spouse Employment Income', standoff=15),
                scaleanchor="x",
                scaleratio=1,
            )
        )
  
        fig.update_layout(height=600, width=800)
        # Add header
        st.markdown("<h3 style='text-align: center; color: black;'>Marriage Incentive and Penalty Analysis</h3>", unsafe_allow_html=True)
        fig = format_fig(fig)
        # Display the chart
        
        st.plotly_chart(fig, use_container_width=True)
    
    get_chart()


