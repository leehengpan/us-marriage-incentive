import pandas as pd
import streamlit as st
import numpy as np
import plotly.express as px
from policyengine_us import Simulation

# Constants
YEAR = "2024"
DEFAULT_AGE = 40

def create_situation_with_axes(state_code, head_employment_income, spouse_employment_income=None, children_ages=None, disability_status=None):
    if children_ages is None:
        children_ages = {}

    situation = {
        "people": {
            "you": {
                "age": {YEAR: DEFAULT_AGE},
                "employment_income": {YEAR: head_employment_income},
                "is_disabled": disability_status['head'] if disability_status else False
            }
        }
    }
    members = ["you"]
    if spouse_employment_income is not None:
        situation["people"]["your partner"] = {
            "age": {YEAR: DEFAULT_AGE},
            "employment_income": {YEAR: spouse_employment_income},
            "is_disabled": disability_status['spouse'] if disability_status else False
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
            "is_disabled": disability_status.get(f'child_{key}', False)
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

def create_net_income_situations_with_axes(state_code, children_ages, disability_status):
    head_employment_income = 80000
    spouse_employment_income = 80000
    married_situation = create_situation_with_axes(state_code, head_employment_income, spouse_employment_income, children_ages, disability_status)
    single_head_situation = create_situation_with_axes(state_code, head_employment_income, None, children_ages, disability_status)
    single_spouse_situation = create_situation_with_axes(state_code, spouse_employment_income, None, {}, disability_status)

    return married_situation, single_head_situation, single_spouse_situation

def calculate_net_income_for_situation(situation):
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

    columns = [str(i) for i in range(0, 90000, 10000)]
    data_frames = {key: pd.DataFrame(value, columns=columns[:value.shape[1]]) for key, value in results.items()}

    combined_df = pd.concat(data_frames, axis=1, keys=data_frames.keys())
    return combined_df

def to_2d_array(array):
    return np.expand_dims(array, axis=1) if array.ndim == 1 else array

def get_net_income_array(situations, tab):
    return [to_2d_array(calculate_net_income_for_situation(s)[(tab,)].to_numpy()) for s in situations]

def calculate_net_income_grid(state_code, children_ages, tab, disability_status):
    situations = create_net_income_situations_with_axes(state_code, children_ages, disability_status)
    net_incomes = get_net_income_array(situations, tab)

    net_income_married_array = net_incomes[0].reshape(9, 9)
    net_income_single_head_array = net_incomes[1]
    net_income_single_spouse_array = net_incomes[2]

    net_income_combined_singles = np.add.outer(
        net_income_single_head_array.flatten(), net_income_single_spouse_array.flatten()
    ).reshape(9, 9)
    net_income_delta = net_income_married_array - net_income_combined_singles

    columns = calculate_net_income_for_situation(situations[0])[(tab,)].columns
    index = calculate_net_income_for_situation(situations[0]).index
    return pd.DataFrame(net_income_delta, columns=columns, index=index)

def create_heatmap_chart(state_code, children_ages, tab, disability_status):
    st.markdown("### Situation with varying head and spouse income:")
    x_values = y_values = list(range(0, 90000, 10000))
    data = calculate_net_income_grid(state_code, children_ages, tab, disability_status)

    if not np.any(data.values):
        return "No changes in the net income data."
    if tab == "Tax Before Refundable Credits":
        data = -data
    abs_max = max(abs(data.min().min()), abs(data.max().max()))
    z_min, z_max = -abs_max, abs_max
    color_scale = [(0, "#616161"), (0.5, "#FFFFFF"), (1, "#2C6496")]

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

    return fig
