# Load data
from dcurves.load_test_data import load_test_surv_risk_test_df
from dcurves.load_test_data import load_survival_df
import dcurves
from dcurves.load_test_data import load_tutorial_bin_marker_risks_list

# load risk functions
from dcurves.risks import _calc_binary_risks, _calc_surv_risks
from dcurves.risks import _create_risks_df

# load tools
import pandas as pd
import numpy as np

def test_bin_dca_risks_calc():

    r_marker_risks = np.round(sorted(load_tutorial_bin_marker_risks_list()['marker_risk'].tolist()), 10)

    df_cancer_dx = \
        pd.read_csv(
            "https://raw.githubusercontent.com/ddsjoberg/dca-tutorial/main/data/df_cancer_dx.csv"
        )

    p_marker_risks = \
        np.round(
            sorted(
                _calc_binary_risks(
                    data=df_cancer_dx,
                    outcome='cancer',
                    model='marker'
                )
            ),
            10
        )

    assert all(r_marker_risks==p_marker_risks)


def test_surv_dca_risks_calc():

    r_surv_risk_test_df = load_test_surv_risk_test_df()

    surv_df = load_survival_df()

    surv_marker_calc_list = \
        _calc_surv_risks(
            data=surv_df,
            outcome='cancer',
            model='marker',
            time=2,
            time_to_outcome_col='ttcancer'
        )

    comp_df = \
        pd.DataFrame({'r_marker_risks': r_surv_risk_test_df['marker'].tolist(),
                      'p_marker_risks': surv_marker_calc_list}).round(decimals=4)

    assert comp_df['r_marker_risks'].equals(comp_df['p_marker_risks'])


def test_rectify_model_risk_boundaries():


    pass

