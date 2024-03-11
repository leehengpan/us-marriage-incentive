import streamlit as st
#
from policyengine_us import Simulation
from policyengine_us.variables.household.demographic.geographic.state_code import (
    StateCode,
)


# Create a function to get net income for the household, married or separate.


def get_net_incomes(state_code, head_employment_income, spouse_employment_income, children_ages = {}):
    # Tuple of net income for separate and married.
    net_income_married = get_net_income(
        state_code, head_employment_income, spouse_employment_income, children_ages
    )
    net_income_head = get_net_income(state_code, head_employment_income, None,children_ages)
    net_income_spouse = get_net_income(state_code, spouse_employment_income, None, children_ages={})
    return net_income_married, net_income_head + net_income_spouse


DEFAULT_AGE = 40


def get_programs(state_code, head_employment_income, spouse_employment_income=None):
    # Start by adding the single head.
    situation = {
        "people": {
            "you": {
                "age": {year: DEFAULT_AGE},
                "employment_income": {year: head_employment_income},
            }
        }
    }
    members = ["you"]
    if spouse_employment_income is not None:
        situation["people"]["your partner"] = {
            "age": {year: DEFAULT_AGE},
            "employment_income": {year: spouse_employment_income},
        }
        # Add your partner to members list.
        members.append("your partner")
    # Create all parent entities.
    situation["families"] = {"your family": {"members": members}}
    situation["marital_units"] = {"your marital unit": {"members": members}}
    situation["tax_units"] = {"your tax unit": {"members": members}}
    situation["spm_units"] = {"your spm_unit": {"members": members}}
    situation["households"] = {
        "your household": {"members": members, "state_name": {year: state_code}}
    }

    simulation = Simulation(situation=situation)
    household_market_income = int(simulation.calculate( "household_market_income", 2023)[0])
    household_benefits = int(simulation.calculate("household_benefits", 2023)[0])
    household_refundable_tax_credits = int(simulation.calculate("household_refundable_tax_credits", 2023)[0])
    household_refundable_tax_credits = int(simulation.calculate("household_refundable_tax_credits", 2023)[0])
    household_tax_before_refundable_credits = int(simulation.calculate("household_tax_before_refundable_credits", 2023)[0])
   

    return [household_market_income ,household_benefits ,household_refundable_tax_credits,household_tax_before_refundable_credits]
def get_categorized_programs(state_code, head_employment_income, spouse_employment_income):
     programs_married = get_programs(state_code, head_employment_income, spouse_employment_income)
     programs_head = get_programs(state_code, head_employment_income)
     programs_spouse = get_programs(state_code, spouse_employment_income)
     return [programs_married, programs_head, programs_spouse]

# Create a function to get net income for household
def get_net_income(state_code, head_employment_income, spouse_employment_income=None, children_ages = {}):
    # Start by adding the single head.
    situation = {
        "people": {
            "you": {
                "age": {"2023": DEFAULT_AGE},
                "employment_income": {"2023": head_employment_income},
            }
        }
    }
    members = ["you"]
    if spouse_employment_income is not None:
        situation["people"]["your partner"] = {
            "age": {"2023": DEFAULT_AGE},
            "employment_income": {"2023": spouse_employment_income},
        }
        # Add your partner to members list.
        members.append("your partner")
    for key, value in children_ages.items():
        situation["people"][f"child {key}"] = {
            "age": {"2023": value}
        }
        # Add child to members list.
        members.append(f"child {key}")
    # Create all parent entities.
    situation["families"] = {"your family": {"members": members}}
    situation["marital_units"] = {"your marital unit": {"members": members}}
    situation["tax_units"] = {"your tax unit": {"members": members}}
    situation["spm_units"] = {"your spm_unit": {"members": members}}
    situation["households"] = {
        "your household": {"members": members, "state_name": {"2023": state_code}}
    }

    simulation = Simulation(situation=situation)

    return simulation.calculate("household_net_income", int(year))[0]

#Streamlit heading and description
header = st.header("Marriage Incentive Calculator")  
header_description = st.write("This application evaluates marriage penalties and bonuses of couples, based on state and individual employment income")
repo_link = st.markdown("This application utilizes <a href='https://github.com/PolicyEngine/us-marriage-incentive'>the policyengine API</a>", unsafe_allow_html=True)  


# Create Streamlit inputs for state code, head income, and spouse income.
options = [s.value for s in StateCode]
state_code = st.selectbox("State Code", options)

# Select box for state
year = "2024"
head_employment_income = st.number_input("Head Employment Income", 0)
spouse_employment_income = st.number_input("Spouse Employment Income", 0)
num_children = st.number_input("Number of Children", 0)
children_ages = {}
for num in range(1,num_children + 1):
    children_ages[num] = st.number_input(f"Child {num} Age", 0)
#submit button
submit = st.button("Calculate")
# Get net incomes.
if submit:
    net_income_married, net_income_separate = get_net_incomes(
        state_code, head_employment_income, spouse_employment_income, children_ages
    )
    programs = get_categorized_programs(state_code, head_employment_income, spouse_employment_income)
    married_programs = programs[0]
    head_separate = programs[1]
    spouse_separate = programs[2]
    separate = [x + y for x, y in zip(head_separate, spouse_separate)]
    delta = [x - y for x, y in zip(married_programs, separate)]

    programs = ["household_market_income", "household_benefits", "household_refundable_tax_credits", "household_tax_before_refundable_credits"]



    # Determine marriage penalty or bonus, and extent in dollars and percentage.
    marriage_bonus = net_income_married - net_income_separate
    marriage_bonus_percent = marriage_bonus / net_income_married


    # Display net incomes in Streamlit.
    st.write("Net Income Married: ", "${:,}".format(round(net_income_married)))
    st.write("Net Income Not Married: ", "${:,}".format(round(net_income_separate)))

    # Display marriage bonus or penalty in Streamlit as a sentence.
    # For example, "You face a marriage [PENALTY/BONUS]"
    # "If you file separately, your combined net income will be [X] [more/less] (y%) than if you file together."


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
    # Sample data
    data = {
        'Program': programs,
        'Married': "${:,}".format(round(married_programs[0])), 
        'Not Married': "${:,}".format(round(separate[0])),
        'Delta ': "${:,}".format(round(delta[0]))
    }

    # Create a DataFrame
    #df = pd.DataFrame(data)

    # Display the table in Streamlit
    st.table(data)