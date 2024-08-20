import pandas as pd
import numpy as np
from policyengine_us import Simulation
from policyengine_us.variables.household.income.household.household_benefits import household_benefits as HouseholdBenefits
from policyengine_us.variables.household.income.household.household_tax_before_refundable_credits import household_tax_before_refundable_credits as HouseholdTaxBeforeRefundableCredits
import pkg_resources
import yaml
import copy

# Constants
YEAR = "2024"
DEFAULT_AGE = 40

def load_credits_from_yaml(package, resource_path):
    yaml_file = pkg_resources.resource_stream(package, resource_path)
    data = yaml.safe_load(yaml_file)
    newest_year = max(data["values"].keys())
    credits = data["values"].get(newest_year, [])
    return credits

def create_situation(state_code, head_income, is_disabled, spouse_income=None, children_ages=None):
    if children_ages is None:
        children_ages = {}

    situation = {
        "people": {
            "you": {
                "age": {YEAR: DEFAULT_AGE},
                "employment_income": {YEAR: head_income},
                "is_disabled": is_disabled['head']
            }
        }
    }
    members = ["you"]
    marital_unit_members = ["you"]
    if spouse_income is not None:
        situation["people"]["your partner"] = {
            "age": {YEAR: DEFAULT_AGE},
            "employment_income": {YEAR: spouse_income},
            "is_disabled": is_disabled['spouse']
        }
        members.append("your partner")
        marital_unit_members.append("your partner")
    if children_ages:
        for key, value in children_ages.items():
            situation["people"][f"child_{key}"] = {
                "age": value,
                "employment_income": {YEAR: 0},
                "is_disabled": is_disabled[f'child_{key}']
            }
            members.append(f"child_{key}")
    
    situation["families"] = {"your family": {"members": members}}
    situation["marital_units"] = {"your marital unit": {"members": marital_unit_members}}
    # add marrital units for children
    for key, value in children_ages.items():
        situation["marital_units"][f"child_{key}'s marital unit"] = {"marital_unit_id": {YEAR: int(key)},"members": [f"child_{key}"]}

    situation["tax_units"] = {"your tax unit": {"members": members}}
    situation["spm_units"] = {"your spm_unit": {"members": members}}
    situation["households"] = {
        "your household": {"members": members, "state_name": {YEAR: state_code}}
    }
    return situation

def calculate_values(categories, simulation, year):
    result_dict = {}
    for category in categories:
        amount = int(simulation.calculate(category, year, map_to="household")[0])
        result_dict[category] = amount
    return result_dict

def get_programs(state_code, head_employment_income, disability_status, spouse_employment_income=None, children_ages=None):
    situation = create_situation(state_code, head_employment_income, disability_status, spouse_employment_income, children_ages)
    simulation = Simulation(situation=situation)

    benefits_categories = HouseholdBenefits.adds
    taxes_before_refundable_credits = HouseholdTaxBeforeRefundableCredits.adds

    package = "policyengine_us"
    resource_path_federal = "parameters/gov/irs/credits/refundable.yaml"
    resource_path_state = f"parameters/gov/states/{state_code.lower()}/tax/income/credits/refundable.yaml"

    try:
        refundable_credits_federal = load_credits_from_yaml(package, resource_path_federal)
    except FileNotFoundError:
        refundable_credits_federal = []

    try:
        refundable_credits_state = load_credits_from_yaml(package, resource_path_state)
    except FileNotFoundError:
        refundable_credits_state = []

    refundable_credits = refundable_credits_federal + refundable_credits_state

    household_net_income = int(simulation.calculate("household_net_income", YEAR))
    household_benefits = int(simulation.calculate("household_benefits", YEAR))
    household_refundable_tax_credits = int(simulation.calculate("household_refundable_tax_credits", int(YEAR)))
    household_tax_before_refundable_credits = int(simulation.calculate("household_tax_before_refundable_credits", int(YEAR)))

    benefits_dict = calculate_values(benefits_categories, simulation, YEAR)
    credits_dict = calculate_values(refundable_credits, simulation, YEAR)
    taxes_before_refundable_credits_dict = calculate_values(taxes_before_refundable_credits, simulation, YEAR)

    return [
        household_net_income,
        household_benefits,
        household_refundable_tax_credits,
        household_tax_before_refundable_credits,
        taxes_before_refundable_credits_dict,
        benefits_dict,
        credits_dict,
    ]


def get_categorized_programs(state_code, head_employment_income, spouse_employment_income, children_ages, disability_status):
    programs_married = get_programs(state_code, head_employment_income, disability_status, spouse_employment_income, children_ages)
    programs_head_if_single_with_children = get_programs(state_code, head_employment_income, disability_status, None, children_ages)
    disability_status_spouse_as_head = copy.deepcopy(disability_status)
    disability_status_spouse_as_head['head'] = disability_status['spouse']
    del disability_status_spouse_as_head['spouse']
    programs_spouse_if_single_without_children = get_programs(state_code, spouse_employment_income, disability_status_spouse_as_head, None, {})
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

def create_table_data(categories, married_values, separate_values, tab_name, filter_zeros=True):
    formatted_married, formatted_separate, formatted_delta, formatted_delta_percent = calculate_deltas(married_values, separate_values)

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
        df = df[(df["Married"] != "$0") | (df["Not Married"] != "$0")]
    return df
