import streamlit as st
import plotly.express as px
from policyengine_us import Simulation
import plotly.graph_objects as go
from policyengine_core.charts import format_fig
from plotly.subplots import make_subplots
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
    # Create all parent entities.
    situation["families"] = {"your family": {"members": members}}
    situation["marital_units"] = {"your marital unit": {"members": members}}
    situation["tax_units"] = {"your tax unit": {"members": members}}
    situation["spm_units"] = {"your spm_unit": {"members": members}}
    situation["households"] = {
        "your household": {"members": members, "state_name": {"2023": state_code}}
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

    return simulation.calculate("household_net_income", 2023)[0]

#Streamlit heading and description
header = st.header("Marriage Incentive Calculator")  
header_description = st.write("This application evaluates marriage penalties and bonuses of couples, based on state and individual employment income")
repo_link = st.markdown("This application utilizes the policyengine API <a href='https://github.com/PolicyEngine/us-marriage-incentive'>link</a>", unsafe_allow_html=True)  


# Create Streamlit inputs for state code, head income, and spouse income.
state_code = st.text_input("State Code", "CA")
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
    st.write("Net Income Married: ", net_income_married)
    st.write("Net Income Not Married: ", net_income_separate)

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
    # Sample data
    table_data = {
        'Program': programs,
        'Married': married_programs,
        'Not Married': separate,
        'Delta ': delta
    }

    # Display the table in Streamlit
    st.table(table_data)


    def check_child_influence():
        salary_ranges = [10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000]
        data = []

        for i in range(len(salary_ranges)):
            temp_data = []
            
            for j in range(len(salary_ranges)):
                head_employment_income = salary_ranges[i]
                spouse_employment_income = salary_ranges[j]

                # Assuming get_net_incomes now returns a tuple (net_income_married, net_income_head_spouse)
                net_income_married,  net_income_separate  = get_net_incomes(
                    state_code, head_employment_income, spouse_employment_income
                )
                marriage_bonus = net_income_married - net_income_separate
                if marriage_bonus > 0:
                    if marriage_bonus > 2000:   
                        temp_data.append(1)
                    elif marriage_bonus > 500:
                        temp_data.append(0.8)
                    else:
                        temp_data.append(0.6)
                else:
                    if marriage_bonus < -1000:
                        temp_data.append(0)
                    elif marriage_bonus < -500:
                        temp_data.append(0.2)
                    else:
                        temp_data.append(0.4)

            data.append(temp_data)

        return data

        
    def get_chart():
    # Function to calculate the input data (replace with your actual data calculation)
        # Set numerical values for x and y axes
        x_values = [10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000]
        y_values = [10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000]

        # Display loading spinner while calculating data
        with st.spinner("Calculating Heatmap... May take 90 seconds"):
            # Calculate data (replace with your actual data calculation)
            data = check_child_influence()

        # Display the chart once data calculation is complete
        fig = px.imshow(data,
                        labels=dict(x="Head Employment Income", y="Spouse Employment Income", color="Bonus"),
                        x=x_values,
                        y=y_values,
                        color_continuous_scale=[[0, "#616161" ],[0.2, "#D2D2D2"], [0.4, "#BDBDBD"], [0.6, "#D8E6F3"],[0.8, "#B1CDE3"], [1, "#2C6496"]],
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

        # Display the chart
        st.plotly_chart(fig, use_container_width=True)
    
    get_chart()


