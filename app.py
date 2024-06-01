import streamlit as st
from policyengine_us import Simulation
from policyengine_us.variables.household.demographic.geographic.state_code import (
    StateCode,
)
from policyengine_us.variables.household.income.household.household_benefits import (
    household_benefits as HouseholdBenefits,
)
from policyengine_us.variables.household.income.household.household_tax_before_refundable_credits import (household_tax_before_refundable_credits as HouseholdTaxBeforeRefundableCredits,)

import pandas as pd

import yaml
import pkg_resources
import datetime


def load_credits_from_yaml(package, resource_path):
    yaml_file = pkg_resources.resource_stream(package, resource_path)
    data = yaml.safe_load(yaml_file)
    # Find the newest available year
    newest_year = max(data['values'].keys())
    credits = data['values'].get(newest_year, [])

    return credits


# Constants
DEFAULT_AGE = 40
YEAR = "2024"

# Streamlit heading and description
st.header("Marriage Incentive Calculator")
st.write(
    "This application evaluates marriage penalties and bonuses of couples, based on state and individual employment income"
)
st.markdown("This application utilizes the [`policyengine-us` Python package](https://github.com/policyengine/policyengine-us).",)

# Streamlit inputs for state code, head income, and spouse income.
statecodes = [s.value for s in StateCode]
US_TERRITORIES = {
    "GU": "Guam",
    "MP": "Northern Mariana Islands",
    "PW": "Palau",
    "PR": "Puerto Rico",
    "VI": "Virgin Islands",
    "AA": "Armed Forces Americas (Except Canada)",
    "AE": "Armed Forces Africa/Canada/Europe/Middle East",
    "AP": "Armed Forces Pacific",
}
options = [value for value in statecodes if value not in US_TERRITORIES]
state_code = st.selectbox("State Code", options)
head_employment_income = st.number_input(
    "Head Employment Income", min_value=0, step=10000, value=0
)
spouse_employment_income = st.number_input(
    "Spouse Employment Income", min_value=0, step=10000, value=0
)
num_children = st.number_input("Number of Children", 0)
children_ages = {
    num: st.number_input(f"Child {num} Age", 0) for num in range(1, num_children + 1)
}

# Submit button
submit = st.button("Calculate")


def create_situation(state_code, head_income, spouse_income=None, children_ages=None):
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
            }
        }
    }
    members = ["you"]
    if spouse_income is not None:
        situation["people"]["your partner"] = {
            "age": {YEAR: DEFAULT_AGE},
            "employment_income": {YEAR: spouse_income},
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
        state_code, head_employment_income, spouse_employment_income, children_ages
    )
    simulation = Simulation(situation=situation)

    benefits_categories = HouseholdBenefits.adds

    taxes_before_refundable_credits = HouseholdTaxBeforeRefundableCredits.adds

    package = "policyengine_us"
    resource_path_federal = "parameters/gov/irs/credits/refundable.yaml"
    resource_path_state = f"parameters/gov/states/{state_code.lower()}/tax/income/credits/refundable.yaml"

    # Load refundable credits for both paths
    refundable_credits_federal = load_credits_from_yaml(package, resource_path_federal)
    refundable_credits_state = load_credits_from_yaml(package, resource_path_state)

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
        benefit_amount = int(
            simulation.calculate(benefit, YEAR, map_to="household")[0]
        )
        benefits_dict[benefit] = benefit_amount

    credits_dic = {}
    for credit in refundable_credits:
        credit_amount = int(
            simulation.calculate(credit, YEAR, map_to="household")[0]
        )
        credits_dic[credit] = credit_amount

    taxes_before_refundable_credits_dic = {}
    for tax in taxes_before_refundable_credits:
        tax_amount = int(
            simulation.calculate(tax, YEAR, map_to="household")[0]
        )
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


def summarize_marriage_bonus(marriage_bonus, marriage_bonus_percent):
    """
    Create a string to summarize the marriage bonus or penalty.
    """
    return (
        f"If you file separately, your combined net income will be ${abs(marriage_bonus):,.2f} "
        f"{'less' if marriage_bonus < 0 else 'more'} "
        f"({abs(marriage_bonus_percent):.1%}) than if you file together."
    )


def format_program_name(name):
    return name.replace('_', ' ').title()

def calculate_deltas(married, separate):
    delta = [x - y for x, y in zip(married, separate)]
    delta_percent = [(x - y) / y if y != 0 else 0 for x, y in zip(married, separate)]

    formatted_married = list(map(lambda x: "${:,}".format(round(x)), married))
    formatted_separate = list(map(lambda x: "${:,}".format(round(x)), separate))
    formatted_delta = list(map(lambda x: "${:,}".format(round(x)), delta))
    formatted_delta_percent = list(map(lambda x: "{:.1%}".format(x), delta_percent))

    return formatted_married, formatted_separate, formatted_delta, formatted_delta_percent



if submit:
    package = "policyengine_us"
    resource_path_federal = "parameters/gov/irs/credits/refundable.yaml"
    resource_path_state = f"parameters/gov/states/{state_code.lower()}/tax/income/credits/refundable.yaml"

    # Load refundable credits for both paths
    refundable_credits_federal = load_credits_from_yaml(package, resource_path_federal)
    refundable_credits_state = load_credits_from_yaml(package, resource_path_state)

    # Ensure refundable_credits is the same shape as refundable_credits_federal
    refundable_credits = refundable_credits_federal + refundable_credits_state
    
    programs = get_categorized_programs(
        state_code, head_employment_income, spouse_employment_income, children_ages
    )

if submit:
    programs = get_categorized_programs(
        state_code, head_employment_income, spouse_employment_income, children_ages
    )

    married_programs = programs[0][:-3]
    head_separate = programs[1][:-3]
    spouse_separate = programs[2][:-3]
    separate = [x + y for x, y in zip(head_separate, spouse_separate)]

    formatted_married_programs, formatted_separate, formatted_delta, formatted_delta_percent = calculate_deltas(married_programs, separate)

    programs_list = [
        "Net income",
        "Benefits",
        "Refundable tax credits",
        "Taxes before refundable credits",
    ]

    table_data = {
        "Program": programs_list,
        "Not Married": formatted_separate,
        "Married": formatted_married_programs,
        "Delta": formatted_delta,
        "Delta Percentage": formatted_delta_percent,
    }

    table_df = pd.DataFrame(table_data)



    benefits_categories = list(programs[0][-2].keys())
    benefits_married = list(programs[0][-2].values())
    benefits_head = list(programs[1][-2].values())
    benefits_spouse = list(programs[2][-2].values())
    benefits_separate = [x + y for x, y in zip(benefits_head, benefits_spouse)]

    formatted_benefits_married, formatted_benefits_separate, formatted_benefits_delta, formatted_benefits_delta_percent = calculate_deltas(benefits_married, benefits_separate)

    # Benefits Table 

    benefits_table = {
        "Program": [],
        "Not Married": [],
        "Married": [],
        "Delta": [],
        "Delta Percentage": [],
    }

    for i, benefit in enumerate(benefits_categories):
        if benefits_married[i] != 0 or benefits_separate[i] != 0:
            benefits_table["Program"].append(format_program_name(benefit))
            benefits_table["Not Married"].append(formatted_benefits_separate[i])
            benefits_table["Married"].append(formatted_benefits_married[i])
            benefits_table["Delta"].append(formatted_benefits_delta[i])
            benefits_table["Delta Percentage"].append(formatted_benefits_delta_percent[i])

    benefits_df = pd.DataFrame(benefits_table)

    # The Credits before refudnable credits Table 


    credits_table = {
        "Program": [],
        "Not Married": [],
        "Married": [],
        "Delta": [],
        "Delta Percentage": [],
    }

    credits_categories = list(programs[0][-1].keys())
    credits_married = list(programs[0][-1].values())
    credits_head = list(programs[1][-1].values())
    credits_spouse = list(programs[2][-1].values())
    credits_separate = [x + y for x, y in zip(credits_head, credits_spouse)]

    formatted_credits_married, formatted_credits_separate, formatted_credits_delta, formatted_credits_delta_percent = calculate_deltas(credits_married, credits_separate)

    credits_table = {
        "Program": [],
        "Not Married": [],
        "Married": [],
        "Delta": [],
        "Delta Percentage": [],
    }

    for i, credits in enumerate(refundable_credits):
        if credits_married[i] != 0 or credits_separate[i] != 0:
            credits_table["Program"].append(format_program_name(credits))
            credits_table["Not Married"].append(formatted_credits_separate[i])
            credits_table["Married"].append(formatted_credits_married[i])
            credits_table["Delta"].append(formatted_credits_delta[i])
            credits_table["Delta Percentage"].append(formatted_credits_delta_percent[i])

    refundable_credits_df = pd.DataFrame(credits_table)

    taxes_before_refundable_credits = list(programs[0][-3].keys())
    taxes_married = list(programs[0][-3].values())
    taxes_head = list(programs[1][-3].values())
    taxes_spouse = list(programs[2][-3].values())
    taxes_separate = [x + y for x, y in zip(taxes_head, taxes_spouse)]

    formatted_taxes_married, formatted_taxes_separate, formatted_taxes_delta, formatted_taxes_delta_percent = calculate_deltas(taxes_married, taxes_separate)

    taxes_table = {
        "Program": [],
        "Not Married": [],
        "Married": [],
        "Delta": [],
        "Delta Percentage": [],
    }

    for i, taxes in enumerate(taxes_before_refundable_credits):
        if taxes_married[i] != 0 or taxes_separate[i] != 0:
            taxes_table["Program"].append(format_program_name(taxes))
            taxes_table["Not Married"].append(formatted_taxes_separate[i])
            taxes_table["Married"].append(formatted_taxes_married[i])
            taxes_table["Delta"].append(formatted_taxes_delta[i])
            taxes_table["Delta Percentage"].append(formatted_taxes_delta_percent[i])

    taxes_df = pd.DataFrame(taxes_table)


    tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Benefits Breakdown", "Refundable Credits", "Taxes before Refundable Credits"])
    with tab1:
        st.dataframe(table_df, hide_index=True)
    with tab2:
        st.dataframe(benefits_df, hide_index=True)
    with tab3:
        st.dataframe(refundable_credits_df, hide_index=True)
    with tab4:
        st.dataframe(taxes_df, hide_index=True)
