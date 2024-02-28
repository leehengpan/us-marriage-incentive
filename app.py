import streamlit as st

#
from policyengine_us import Simulation


# Create a function to get net income for the household, married or separate.


def get_net_incomes(state_code, head_employment_income, spouse_employment_income):
    # Tuple of net income for separate and married.
    net_income_married = get_net_income(
        state_code, head_employment_income, spouse_employment_income
    )
    net_income_head = get_net_income(state_code, head_employment_income)
    net_income_spouse = get_net_income(state_code, spouse_employment_income)
    return net_income_married, net_income_head + net_income_spouse


DEFAULT_AGE = 40

# Create a function to get net income for household
def get_net_income(state_code, head_employment_income, spouse_employment_income=None):
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

    return simulation.calculate("household_net_income", int(year))[0]


# Create Streamlit inputs for state code, head income, and spouse income.
state_code = st.text_input("State Code", "CA")
year_options = ["2023", "2022", "2021", "2020"]

# Select box for state
year = st.selectbox(
    "Select Year",
    options=year_options
)
head_employment_income = st.number_input("Head Employment Income", 0)
spouse_employment_income = st.number_input("Spouse Employment Income", 0)

# Get net incomes.
net_income_married, net_income_separate = get_net_incomes(
    state_code, head_employment_income, spouse_employment_income
)

# Determine marriage penalty or bonus, and extent in dollars and percentage.
marriage_bonus = net_income_married - net_income_separate
marriage_bonus_percent = marriage_bonus / net_income_married


# Display net incomes in Streamlit.
st.write("Net Income Married: ", net_income_married)
st.write("Net Income Separate: ", net_income_separate)

# Display marriage bonus or penalty in Streamlit as a sentence.
# For example, "You face a marriage [PENALTY/BONUS]"
# "If you file separately, your combined net income will be [X] [more/less] (y%) than if you file together."


def summarize_marriage_bonus(marriage_bonus):
    # Create a string to summarize the marriage bonus or penalty.
    return (
        f"If you file separately, your combined net income will be ${abs(marriage_bonus):,.2f} "
        f"{'less' if marriage_bonus > 0 else 'more'} "
        f"({abs(marriage_bonus_percent):.2f}%) than if you file together."
    )


if marriage_bonus > 0:
    st.write("You face a marriage BONUS.")
elif marriage_bonus < 0:
    st.write("You face a marriage PENALTY.")
else:
    st.write("You face no marriage penalty or bonus.")

st.write(summarize_marriage_bonus(marriage_bonus))
