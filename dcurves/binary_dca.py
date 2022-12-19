import pandas as pd
import numpy as np
import statsmodels.api as sm
import lifelines
import matplotlib.pyplot as plt
from dcurves import _validate
from beartype import beartype

# 221112 SP: Go back and fix prevalence type hinting
# Issue is that while beartype input validation decorator should be a float,
# we also need to allow for input of None in case user wants the default calculated prevalence value
# In short, issue is that prevalence needs to have 2 type hints and beartype has to accept either as valid input

# For now, set prev. type hint to object to bypass issue
@beartype
def _binary_convert_to_risk(
        model_frame: pd.DataFrame,
        outcome: str,
        predictors_to_prob: list
) -> pd.DataFrame:
    # Converts indicated predictor columns in dataframe into probabilities from 0 to 1
    for predictor in predictors_to_prob:
        predicted_vals = sm.formula.glm(outcome + '~' + predictor, family=sm.families.Binomial(),
                                        data=model_frame).fit().predict()
        model_frame[predictor] = [(1 - val) for val in predicted_vals]
        # model_frame.loc[model_frame['predictor']]
    return model_frame




# 221113 SP: Go back and fix prevalence type hinting
# Issue is that while beartype input validation decorator should be a float,
# we also need to allow for input of None in case user wants the default calculated prevalence value
# In short, issue is that prevalence needs to have 2 type hints and beartype has to accept either as valid input

# For now, set prev. type hint to object to bypass issue

@beartype
def _binary_calculate_test_consequences(
        model_frame: pd.DataFrame,
        outcome: str,
        predictor: str,
        thresholds: list,
        prevalence: float = -1.0) -> pd.DataFrame:

    _validate._binary_calculate_test_consequences_input_checks(
        thresholds=thresholds
    )

    # Handle prevalence values
    # If provided: use user-supplied prev value for outcome (case-control)
    # If not provided: calculate

    #### If case-control prevalence:
    if prevalence != -1.0:
        prevalence_values = [prevalence] * len(thresholds)  #### need list to be as long as len(thresholds)
    elif prevalence == -1.0:
        outcome_values = model_frame[outcome].values.flatten().tolist()
        prevalence_values = [pd.Series(outcome_values).value_counts()[1] / len(outcome_values)] * len(
            thresholds)  # need list to be as long as len(thresholds)

    n = len(model_frame.index)
    df = pd.DataFrame({'predictor': predictor,
                       'threshold': thresholds,
                       'n': [n] * len(thresholds),
                       'prevalence': prevalence_values})

    true_outcome = model_frame[model_frame[outcome] == True][[predictor]]
    false_outcome = model_frame[model_frame[outcome] == False][[predictor]]

    test_pos_rate = []
    tp_rate = []
    fp_rate = []

    for (threshold, prevalence) in zip(thresholds, prevalence_values):

        #### Indexing [1] doesn't work w/ value_counts when only index is 0, so [1] gives error, have to try/except so that when [1] doesn't work can input 0

        try:
            test_pos_rate.append(
                pd.Series(model_frame[predictor] >= threshold).value_counts()[1] / len(model_frame.index))
        except KeyError:
            test_pos_rate.append(0 / len(model_frame.index))

        try:
            tp_rate.append(
                pd.Series(true_outcome[predictor] >= threshold).value_counts()[1] / len(true_outcome[predictor]) * (
                    prevalence))
        except KeyError:
            tp_rate.append(0 / len(true_outcome[predictor]) * prevalence)

        try:
            fp_rate.append(pd.Series(false_outcome[predictor] >= threshold).value_counts()[1] / len(
                false_outcome[predictor]) * (1 - prevalence))
        except KeyError:
            fp_rate.append(0 / len(false_outcome[predictor]) * (1 - prevalence))

    df['test_pos_rate'] = test_pos_rate
    df['tpr'] = tp_rate
    df['fpr'] = fp_rate

    return df


@beartype
def binary_dca(
        data: pd.DataFrame,
        outcome: str,
        predictors: list,
        harm: dict,
        predictors_to_prob: list,
        thresh_vals: list = [0.01, 0.99, 0.01],
        prevalence: float = -1.0) -> object:

    # make model_frame df of outcome and predictor cols from data

    model_frame = data[np.append(outcome, predictors)]

    #### Convert to risk
    #### Convert selected columns to risk scores

    model_frame = \
        _binary_convert_to_risk(
            model_frame=model_frame,
            outcome=outcome,
            predictors_to_prob=predictors_to_prob
        )

    # 221218 SP: In R dcurves, vals for 'all' are 1 + epsilon, and
    # vals for 'none' are 1 - epsilon
    model_frame['all'] = [1 for i in range(0, len(model_frame.index))]
    model_frame['none'] = [0 for i in range(0, len(model_frame.index))]

    # thresh_vals input from user contains 3 values: lower threshold bound, higher threshold
    # bound, step increment in positions [0,1,2]

    # nr.arange takes 3 vals: start, stop + one step increment, and step increment
    thresholds = np.arange(thresh_vals[0], thresh_vals[1] + thresh_vals[2], thresh_vals[2])  # array of values
    #### Prep data, add placeholder for 0 (10e-10), because can't use 0  for DCA, will output incorrect (incorrect?) value
    thresholds = np.insert(thresholds, 0, 0.1 ** 9).tolist()

    # Get names of covariates (if survival, then will still have time_to_outcome_col
    covariate_names = [i for i in model_frame.columns if i not in outcome]

    testcons_list = []

    for i in range(0, len(covariate_names)):
        temp_testcons_df = _binary_calculate_test_consequences(
            model_frame=model_frame,
            outcome=outcome,
            predictor=covariate_names[i],
            thresholds=thresholds,
            prevalence=prevalence
        )


        temp_testcons_df['variable'] = [covariate_names[i]] * len(temp_testcons_df.index)

        temp_testcons_df['harm'] = \
            [harm[covariate_names[i]] if covariate_names[i] in harm else 0] * len(temp_testcons_df.index)
        testcons_list.append(temp_testcons_df)

    all_covariates_df = pd.concat(testcons_list)

    all_covariates_df['net_benefit'] = all_covariates_df['tpr'] - all_covariates_df['threshold'] / (
            1 - all_covariates_df['threshold']) * all_covariates_df['fpr'] - all_covariates_df['harm']

    return all_covariates_df




binary_dca.__doc__ = """

    Perform Decision Curve Analysis

    |

    Diagnostic and prognostic models are typically evaluated with measures of
    accuracy that do not address clinical consequences.

    |

    Decision-analytic techniques allow assessment of clinical outcomes but often
    require collection of additional information may be cumbersome to apply to
    models that yield a continuous result. Decision curve analysis is a method
    for evaluating and comparing prediction models that incorporates clinical
    consequences, requires only the data set on which the models are tested,
    and can be applied to models that have either continuous or dichotomous
    results.
    The dca function performs decision curve analysis for binary outcomes.

    |

    Review the
    [DCA Vignette](http://www.danieldsjoberg.com/dcurves/articles/dca.html)
    for a detailed walk-through of various applications.

    |

    Also, see [www.decisioncurveanalysis.org]
    (https://www.mskcc.org/departments/epidemiology-biostatistics/biostatistics/decision-curve-analysis) for more information.

    |

    Examples
    ________
    
    |
    
    from dcurves.binary_dca import binary_dca, surv_dca
    

    |

    Load simulation binary data dataframe, print contents.

    |

    >>> df_binary = dcurves.load_test_data.load_binary_df()
 
    |

    Run DCA on simulation binary data. Print the results.

    |

    >>> bin_dca_result_df = \
    ...   dcurves.dca(
    ...     data = df_binary,
    ...     outcome = 'cancer',
    ...     predictors = ['famhistory']
    ...    )

    |

    Load simulation survival data and run DCA on it. Print the results.

    |
    
    >>> df_surv = load


    Parameters
    ----------
    data : pd.DataFrame
        the data set to analyze
    outcome : str
        the column name of the data frame to use as the outcome
    predictors : str OR list(str)
        the column(s) that will be used to predict the outcome
    thresh_vals : list(float OR int)
        3 values in list - threshold probability lower bound, upper bound,
        then step size, respectively (defaults to [0.01, 1, 0.01]). The lower
        bound must be >0.
    harm : float or list(float)
        the harm associated with each predictor
        harm must have the same length as the predictors list
    probabilities : bool or list(bool)
        whether the predictor is coded as a probability
        probability must have the same length as the predictors list
    time : float (defaults to None)
        survival endpoint time for risk calculation
    prevalence : float (defaults to None)
        population prevalence value
    time_to_outcome_col : str (defaults to None)
        name of input dataframe column that contains time-to-outcome data


    Return
    -------
    all_covariates_df : pd.DataFrame
        A dataframe containing calculated net benefit values and threshold values for plotting

    """



