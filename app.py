import streamlit as st
from policyengine_us import Simulation
from policyengine_us.variables.household.demographic.geographic.state_code import StateCode
from policyengine_us.variables.household.income.household.household_benefits import household_benefits as HouseholdBenefits
from policyengine_us.variables.household.income.household.household_tax_before_refundable_credits import household_tax_before_refundable_credits as HouseholdTaxBeforeRefundableCredits
import numpy as np
import pandas as pd
import yaml
import pkg_resources
import plotly.express as px

# Constants
DEFAULT_AGE = 40
YEAR = "2024"

def load_credits_from_yaml(package, resource_path):
    yaml_file = pkg_resources.resource_stream(package, resource_path)
    data = yaml.safe_load(yaml_file)
    newest_year = max(data["values"].keys())
    credits = data["values"].get(newest_year, [])
    return credits


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
head_disability = st.checkbox("Head is disabled")
spouse_employment_income = st.number_input("Spouse Employment Income", min_value=0, step=10000, value=0)
spouse_disability = st.checkbox("Spouse is disabled")
num_children = st.number_input("Number of Children", 0)
children_ages = {num: st.number_input(f"Child {num} Age", 0) for num in range(1, num_children + 1)}
disability_status = {"head": head_disability, "spouse": spouse_disability}
submit = st.button("Calculate")


def create_situation(state_code, head_income,is_disabled, spouse_income=None, children_ages=None):
    """
    Create a situation dictionary for the simulation.
    """
    if children_ages is None:
        children_ages = {}

    situation = {
        "people": {
            "you": {
                "age": {YEAR: DEFAULT_AGE},
                "employment_income": {YEAR: head_income},
                "is_disabled": is_disabled['head'] ,
            }
        }
    }
    members = ["you"]
    if spouse_income is not None:
        situation["people"]["your partner"] = {
            "age": {YEAR: DEFAULT_AGE},
            "employment_income": {YEAR: spouse_income},
            "is_disabled": is_disabled['spouse']
        }
        members.append("your partner")
    for key, value in children_ages.items():
        situation["people"][f"child {key}"] = {
            "age": {YEAR: value},
            "employment_income": {YEAR: 0},
        }
        members.append(f"child {key}")
    situation["families"] = {"your family": {"members": members}}
    situation["marital_units"] = {"your marital unit": {"members": members}}
    situation["tax_units"] = {"your tax unit": {"members": members}}
    situation["spm_units"] = {"your spm_unit": {"members": members}}
    situation["households"] = {
        "your household": {"members": members, "state_name": {YEAR: state_code}}
    }
    return situation


def get_programs(
    state_code,
    head_employment_income,
    spouse_employment_income=None,
    children_ages=None,
):
    """
    Retrieve program calculations for the given situation.
    """
    situation = create_situation(


        state_code, head_employment_income,  disability_status, spouse_employment_income, children_ages

    )
    simulation = Simulation(situation=situation)

    benefits_categories = HouseholdBenefits.adds

    taxes_before_refundable_credits = HouseholdTaxBeforeRefundableCredits.adds

    package = "policyengine_us"
    resource_path_federal = "parameters/gov/irs/credits/refundable.yaml"
    resource_path_state = (
        f"parameters/gov/states/{state_code.lower()}/tax/income/credits/refundable.yaml"
    )

    # Load refundable credits for both paths
    try:
        refundable_credits_federal = load_credits_from_yaml(
            package, resource_path_federal
        )
    except FileNotFoundError:
        refundable_credits_federal = []

    try:
        refundable_credits_state = load_credits_from_yaml(package, resource_path_state)
    except FileNotFoundError:
        refundable_credits_state = []

    # Ensure refundable_credits is the same shape as refundable_credits_federal
    refundable_credits = refundable_credits_federal + refundable_credits_state

    household_net_income = int(simulation.calculate("household_net_income", YEAR))
    household_benefits = int(simulation.calculate("household_benefits", YEAR))
    household_refundable_tax_credits = int(
        simulation.calculate("household_refundable_tax_credits", int(YEAR))
    )
    household_tax_before_refundable_credits = int(
        simulation.calculate("household_tax_before_refundable_credits", int(YEAR))
    )

    benefits_dict = {}
    for benefit in benefits_categories:
        benefit_amount = int(simulation.calculate(benefit, YEAR, map_to="household")[0])
        benefits_dict[benefit] = benefit_amount

    credits_dic = {}
    for credit in refundable_credits:
        credit_amount = int(simulation.calculate(credit, YEAR, map_to="household")[0])
        credits_dic[credit] = credit_amount

    taxes_before_refundable_credits_dic = {}
    for tax in taxes_before_refundable_credits:
        tax_amount = int(simulation.calculate(tax, YEAR, map_to="household")[0])
        taxes_before_refundable_credits_dic[tax] = tax_amount

    return [
        household_net_income,
        household_benefits,
        household_refundable_tax_credits,
        household_tax_before_refundable_credits,
        taxes_before_refundable_credits_dic,
        benefits_dict,
        credits_dic,
    ]


def get_categorized_programs(
    state_code, head_employment_income, spouse_employment_income, children_ages
):
    """
    Retrieve program calculations for both married and separate situations.
    """
    programs_married = get_programs(
        state_code, head_employment_income, spouse_employment_income, children_ages
    )
    programs_head_if_single_with_children = get_programs(
        state_code, head_employment_income, None, children_ages
    )
    programs_spouse_if_single_without_children = get_programs(
        state_code, spouse_employment_income, None, {}
    )  # Pass an empty dictionary for children_ages
    return [
        programs_married,
        programs_head_if_single_with_children,
        programs_spouse_if_single_without_children,
    ]



def format_program_name(name):
    return name.replace("_", " ").title()


def calculate_deltas(married, separate):
    delta = [x - y for x, y in zip(married, separate)]
    delta_percent = [(x - y) / y if y != 0 else 0 for x, y in zip(married, separate)]

    formatted_married = list(map(lambda x: "${:,}".format(round(x)), married))
    formatted_separate = list(map(lambda x: "${:,}".format(round(x)), separate))
    formatted_delta = list(map(lambda x: "${:,}".format(round(x)), delta))
    formatted_delta_percent = list(map(lambda x: "{:.1%}".format(x), delta_percent))

    return (
        formatted_married,
        formatted_separate,
        formatted_delta,
        formatted_delta_percent,
    )


def create_table_data(
    categories, married_values, separate_values, tab_name, filter_zeros=True
):
    formatted_married, formatted_separate, formatted_delta, formatted_delta_percent = (
        calculate_deltas(married_values, separate_values)
    )

    table_data = {
        "Program": [format_program_name(cat) for cat in categories],
        "Not Married": formatted_separate,
        "Married": formatted_married,
        "Delta": formatted_delta,
        "Delta Percentage": formatted_delta_percent,
        "Tab": [tab_name] * len(categories),
    }

    df = pd.DataFrame(table_data)
    if filter_zeros:
        # Filter out rows where both "Married" and "Not Married" values are 0
        df = df[(df["Married"] != "$0") | (df["Not Married"] != "$0")]
    return df


if submit:
    programs = get_categorized_programs(
        state_code, head_employment_income, spouse_employment_income, children_ages
    )

    # Total Programs Data
    programs_list = [
        "Net income",
        "Benefits",
        "Refundable tax credits",
        "Taxes before refundable credits",
    ]
    married_programs = programs[0][:-3]
    head_separate = programs[1][:-3]
    spouse_separate = programs[2][:-3]
    separate = [x + y for x, y in zip(head_separate, spouse_separate)]

    total_data = create_table_data(
        programs_list, married_programs, separate, "Summary", filter_zeros=False
    )

    # Benefits Data
    benefits_categories = list(programs[0][-2].keys())
    benefits_married = list(programs[0][-2].values())
    benefits_head = list(programs[1][-2].values())
    benefits_spouse = list(programs[2][-2].values())
    benefits_separate = [x + y for x, y in zip(benefits_head, benefits_spouse)]

    benefits_data = create_table_data(
        benefits_categories, benefits_married, benefits_separate, "Benefits Breakdown"
    )

    # Refundable Credits Data
    credits_categories = list(programs[0][-1].keys())
    credits_married = list(programs[0][-1].values())
    credits_head = list(programs[1][-1].values())
    credits_spouse = list(programs[2][-1].values())
    credits_separate = [x + y for x, y in zip(credits_head, credits_spouse)]

    credits_data = create_table_data(
        credits_categories, credits_married, credits_separate, "Refundable Credits"
    )

    # Taxes Data
    taxes_categories = list(programs[0][-3].keys())
    taxes_married = list(programs[0][-3].values())
    taxes_head = list(programs[1][-3].values())
    taxes_spouse = list(programs[2][-3].values())
    taxes_separate = [x + y for x, y in zip(taxes_head, taxes_spouse)]

    taxes_data = create_table_data(
        taxes_categories,
        taxes_married,
        taxes_separate,
        "Taxes before Refundable Credits",
    )
    # Combine all data into a single DataFrame
    all_data = pd.concat([total_data, benefits_data, credits_data, taxes_data])

    # Filter data for each tab and display
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Summary",
            "Benefits Breakdown",
            "Refundable Credits",
            "Taxes before Refundable Credits",
        ]
    )
    with tab1:
        st.dataframe(
            all_data[all_data["Tab"] == "Summary"].drop(columns=["Tab"]),
            hide_index=True,
        )
    with tab2:
        st.dataframe(
            all_data[all_data["Tab"] == "Benefits Breakdown"].drop(columns=["Tab"]),
            hide_index=True,
        )
    with tab3:
        st.dataframe(
            all_data[all_data["Tab"] == "Refundable Credits"].drop(columns=["Tab"]),
            hide_index=True,
        )
    with tab4:
        st.dataframe(
            all_data[all_data["Tab"] == "Taxes before Refundable Credits"].drop(
                columns=["Tab"]
            ),
            hide_index=True,
        )


### HEATMAP CALCULATION ###


def create_situation_with_axes(
    state_code,
    head_employment_income,
    spouse_employment_income=None,
    children_ages=None,
):
    """
    Create a situation dictionary for the simulation with axes.
    """
    if children_ages is None:
        children_ages = {}

    situation = {
        "people": {
            "you": {
                "age": {YEAR: DEFAULT_AGE},
                "employment_income": {YEAR: head_employment_income},
                "is_disabled": disability_status['head']

            }
        }
    }
    members = ["you"]
    if spouse_employment_income is not None:
        situation["people"]["your partner"] = {
            "age": {YEAR: DEFAULT_AGE},
            "employment_income": {YEAR: spouse_employment_income},
            "is_disabled": disability_status['spouse']
        }
        members.append("your partner")
        situation["axes"] = [
            [
                {
                    "name": "employment_income",
                    "count": 9,
                    "index": 0,
                    "min": 0,
                    "max": 80000,
                    "period": YEAR,
                }
            ],
            [
                {
                    "name": "employment_income",
                    "count": 9,
                    "index": 1,
                    "min": 0,
                    "max": 80000,
                    "period": YEAR,
                }
            ],
        ]
    else:
        situation["axes"] = [
            [
                {
                    "name": "employment_income",
                    "count": 9,
                    "min": 0,
                    "max": 80000,
                    "period": YEAR,
                }
            ]
        ]
    for key, value in children_ages.items():
        situation["people"][f"child {key}"] = {
            "age": {YEAR: value},
            "employment_income": {YEAR: 0},
        }
        members.append(f"child {key}")
    situation["families"] = {"your family": {"members": members}}
    situation["marital_units"] = {"your marital unit": {"members": members}}
    situation["tax_units"] = {"your tax unit": {"members": members}}
    situation["spm_units"] = {"your spm_unit": {"members": members}}
    situation["households"] = {
        "your household": {"members": members, "state_name": {YEAR: state_code}}
    }
    return situation


def create_net_income_situations_with_axes(
    state_code,  children_ages
):
    """
    Create situations for calculating net income for married and single statuses.
    """
    head_employment_income = 80000
    spouse_employment_income = 80000
    # Married situation
    married_situation = create_situation_with_axes(
        state_code, head_employment_income, spouse_employment_income, children_ages
    )

    # Single head of household situation
    single_head_situation = create_situation_with_axes(
        state_code, head_employment_income, None, children_ages
    )

    # Single spouse situation (assuming no children for the spouse when single)
    single_spouse_situation = create_situation_with_axes(
        state_code, spouse_employment_income, None, {}
    )

    return married_situation, single_head_situation, single_spouse_situation



def calculate_net_income_for_situation(situation):
    """
    Calculate the net income, benefits, refundable tax credits, and tax before refundable credits
    for a given situation using the Simulation class.
    """
    def calculate_and_process(name):
        result = np.array(simulation.calculate(name, YEAR))
        if result.ndim == 1:
            result = np.expand_dims(result, axis=1)
        if result.size == 81:
            return result.reshape(9, 9)
        elif result.size == 9:
            return result.reshape(9, 1)
        else:
            raise ValueError(f"Unexpected size for {name}: {result.size}")
    
    simulation = Simulation(situation=situation)
    
    results = {
        "Net Income": calculate_and_process("household_net_income"),
        "Benefits": calculate_and_process("household_benefits"),
        "Refundable Tax Credits": calculate_and_process("household_refundable_tax_credits"),
        "Tax Before Refundable Credits": calculate_and_process("household_tax_before_refundable_credits")
    }

    # Create DataFrames
    columns = [str(i) for i in range(0, 90000, 10000)]
    data_frames = {key: pd.DataFrame(value, columns=columns[:value.shape[1]]) for key, value in results.items()}
    
    # Combine DataFrames into a single DataFrame with multi-level columns
    combined_df = pd.concat(data_frames, axis=1, keys=data_frames.keys())
    return combined_df


def calculate_net_income_grid(state_code, children_ages, tab):
    """
    Calculate the net income for a range of incomes for both the head and spouse.
    """
    def to_2d_array(array):
        return np.expand_dims(array, axis=1) if array.ndim == 1 else array

    # Create situations and calculate net incomes
    situations = create_net_income_situations_with_axes(state_code, children_ages)
    net_incomes = [calculate_net_income_for_situation(s) for s in situations]
    
    # Extract the net income arrays for calculations
    net_income_married_array = net_incomes[0][(tab,)].to_numpy()
    net_income_single_head_array = to_2d_array(net_incomes[1][(tab,)].to_numpy())
    net_income_single_spouse_array = to_2d_array(net_incomes[2][(tab,)].to_numpy())
    
    # Calculate the net income delta
    net_income_combined_singles = np.add.outer(
        net_income_single_head_array.flatten(), net_income_single_spouse_array.flatten()
    ).reshape(9, 9)
    net_income_delta = net_income_married_array - net_income_combined_singles

    # Return DataFrame with proper column and index structure
    columns = net_incomes[0][(tab,)].columns
    index = net_incomes[0].index
    return pd.DataFrame(net_income_delta, columns=columns, index=index)




def create_heatmap_chart(state_code, children_ages, tab):
    """
    Create a heatmap for net income levels for married, single head of household, and single spouse situations.
    """
    x_values = y_values = list(range(0, 90000, 10000))
    data = calculate_net_income_grid(state_code, children_ages, tab)

    # Check if there is any change in data
    if not np.any(data.values):
        st.write("No changes in the net income data.")
        return

    abs_max = max(abs(data.min().min()), abs(data.max().max()))
    z_min, z_max = -abs_max, abs_max
    color_scale = [(0, "#616161"), (0.5, "#FFFFFF"), (1, "#2C6496")]

    # Create heatmap
    fig = px.imshow(
        data,
        labels={"x": "Head Employment Income", "y": "Spouse Employment Income", "color": "Net Change"},
        x=x_values,
        y=y_values,
        zmin=z_min,
        zmax=z_max,
        color_continuous_scale=color_scale,
        origin="lower",
    )

    fig.update_xaxes(side="bottom")
    fig.update_layout(
        xaxis=dict(
            tickmode="array",
            tickvals=x_values,
            ticktext=[f"{val//1000}k" for val in x_values],
            showgrid=True,
            zeroline=False,
            title=dict(text="Head Employment Income", standoff=15),
        ),
        yaxis=dict(
            tickmode="array",
            tickvals=y_values,
            ticktext=[f"{val//1000}k" for val in y_values],
            showgrid=True,
            zeroline=False,
            title=dict(text="Spouse Employment Income", standoff=15),
            scaleanchor="x",
            scaleratio=1,
        ),
        height=600,
        width=800,
    )

    # Add header
    st.markdown(
        f"<h3 style='text-align: center; color: black;'>Heat Map For {tab}</h3>",
        unsafe_allow_html=True,
    )
    
    # Display the chart
    st.plotly_chart(fig, use_container_width=True)

# Usage example in Streamlit app
if submit:
    with tab1:
        create_heatmap_chart(state_code, children_ages, "Net Income")
    with tab2:
        create_heatmap_chart(state_code, children_ages, "Benefits")
    with tab3:
        create_heatmap_chart(state_code, children_ages, "Refundable Tax Credits")
    with tab4:
        create_heatmap_chart(state_code, children_ages, "Tax Before Refundable Credits")