import pandas as pd
import numpy as np
from beartype import beartype
from typing import Optional, Union
import lifelines

from .risks import _create_risks_df, _rectify_model_risk_boundaries


def _calc_prevalence(
        risks_df: pd.DataFrame,
        outcome: str,
        prevalence: Optional[Union[int, float]] = None,
        time: Optional[Union[int, float]] = None,
        time_to_outcome_col: Optional[str] = None
) -> float:
    """
    Parameters
    ----------
    risks_df : pd.DataFrame
        Data containing (converted if necessary) risk scores (scores ranging from 0 to 1 for columns of interest)
    outcome : str
        Column name of outcome of interest in risks_df
    prevalence : int or float. Defaults to None
        Value that indicates the prevalence among the population. Only to be specified in case-control situtations
    time : int or float, Defaults to None
        Time of interest in years, used in Survival DCA
    time_to_outcome_col : str, Defaults to None
        Column name of time of interest in risks_df

    Returns
    -------
    float
        Either calculated prevalence or inutted prevalence depending on whether or not input prevalence was supplied
    """
    # Binary
    if time_to_outcome_col is None:
        if prevalence is not None:
            pass
        elif prevalence is None:
            outcome_values = risks_df[outcome].values.flatten().tolist()
            outcome_tf_counts_dict = dict(pd.Series(outcome_values).value_counts())
            if True not in outcome_tf_counts_dict:
                prevalence = 0 / len(outcome_values)
            else:
                prevalence = outcome_tf_counts_dict[True] / len(outcome_values)
    # Survival
    elif time_to_outcome_col is not None:
        if prevalence is not None:
            ValueError('In survival outcomes, prevalence should not be supplied')
        elif prevalence is None:
            kmf = lifelines.KaplanMeierFitter()
            kmf.fit(risks_df[time_to_outcome_col], risks_df[outcome] * 1)  # *1 to convert from boolean to int
            prevalence = 1 - kmf.survival_function_at_times(time)
            prevalence = float(prevalence)
    return prevalence


@beartype
def _create_initial_df(
        thresholds: np.ndarray,
        modelnames: list,
        input_df_rownum: int,
        prevalence_value: Union[float, int],
        harm: Optional[dict] = None
) -> pd.DataFrame:
    """
    Parameters
    ----------
    thresholds : np.ndarray
        Threshold values (x values) at which net benefit and net interventions avoided will be calculated
    modelnames : list[str]
        Column names from risks_df that contain model risk scores
    input_df_rownum : int
        Number of rows in original input dataframe
    prevalence_value : int or float
        Calculated prevalence value
    harm : dict[float], defaults to None
        Models with their associated harm values

    Returns
    -------

    pd.DataFrame
        DataFrame set with initial parameters
    """
    modelnames = np.append(modelnames, ['all', 'none'])
    initial_df = pd.DataFrame(
        {'model':
             pd.Series([x for y in modelnames for x in [y] * len(thresholds)]),
         'threshold': thresholds.tolist() * len(modelnames),
         'n': [input_df_rownum] * len(thresholds) * len(modelnames),
         'prevalence': [prevalence_value] * len(thresholds) * len(modelnames),
         'harm': 0
         }
    )

    if harm is not None:
        for model in harm.keys():
            initial_df.loc[initial_df['model'] == model, 'harm'] = harm[model]
    elif harm is None:
        pass
    else:
        ValueError('Harm should be either None or dict')

    return initial_df


def _calc_test_pos_rate(
        risks_df: pd.DataFrame,
        thresholds: np.ndarray,
        model: str
) -> pd.Series:
    """
    Parameters
    ----------
    risks_df : pd.DataFrame
        Data containing (converted if necessary) risk scores (scores ranging from 0 to 1 for columns of interest)
    thresholds : np.ndarray
        Threshold values (x values) at which net test positive rate will be calculated
    model : str
        Model column name in risks_df

    Returns
    -------
    pd.Series
        Calculated test positive rates for each threshold value for a model
    """
    test_pos_rate = []

    for threshold in thresholds:
        risk_above_thresh_tf_dict = dict(pd.Series(risks_df[model] >= threshold).value_counts())

        if True not in risk_above_thresh_tf_dict:
            test_pos_rate.append(0 / len(risks_df.index))
        elif True in risk_above_thresh_tf_dict:
            test_pos_rate.append(risk_above_thresh_tf_dict[True] / len(risks_df.index))

    return pd.Series(test_pos_rate)


def _calc_risk_rate_among_test_pos(
        risks_df: pd.DataFrame,
        outcome: str,
        model: str,
        thresholds: np.ndarray,
        time: Union[float, int],
        time_to_outcome_col: str
) -> pd.Series:
    """
    Parameters
    ----------
    risks_df : pd.DataFrame
        Data containing (converted if necessary) risk scores (scores ranging from 0 to 1 for columns of interest)
    outcome : str
        Column name of outcome of interest in risks_df
    model : str
        Model column name in risks_df
    thresholds : np.ndarray
        Threshold values (x values) at which risk rate among test positives will be calculated
    time : int or float
        Time of interest in years, used in Survival DCA
    time_to_outcome_col : str
        Column name of time of interest in risks_df

    Returns
    -------
    pd.Series
        Calculated risk rate among test positive for each threshold value
    """
    risk_rate_among_test_pos = []
    for threshold in thresholds:

        risk_above_thresh_time = risks_df[risks_df[model] >= threshold][time_to_outcome_col]
        risk_above_thresh_outcome = risks_df[risks_df[model] >= threshold][outcome]

        kmf = lifelines.KaplanMeierFitter()

        if np.max(risks_df['ttcancer']) < time:
            risk_rate_among_test_pos.append(None)
        elif len(risk_above_thresh_time) == 0 and len(risk_above_thresh_outcome) == 0:
            risk_rate_among_test_pos.append(float(0))
        else:
            kmf.fit(risk_above_thresh_time, risk_above_thresh_outcome * 1)
            if np.max(kmf.timeline) < time:
                risk_rate_among_test_pos.append(None)
            elif np.max(kmf.timeline) >= time:
                risk_rate_among_test_pos.append(1 - float(kmf.survival_function_at_times(time)))

    return pd.Series(risk_rate_among_test_pos)


def _calc_tp_rate(
        risks_df: pd.DataFrame,
        thresholds: np.ndarray,
        model: str,
        outcome: str,
        test_pos_rate: Optional[pd.Series] = None,
        prevalence_value: Optional[Union[float, int]] = None,
        time: Optional[Union[float, int]] = None,
        time_to_outcome_col: Optional[str] = None
) -> pd.Series:
    """
    Parameters
    ----------
    risks_df : pd.DataFrame
        Data containing (converted if necessary) risk scores (scores ranging from 0 to 1 for columns of interest)
    thresholds : np.ndarray
        Threshold values (x values) at which risk rate among test positives will be calculated
    model : str
        Model column name in risks_df
    outcome : str
        Column name of outcome of interest in risks_df
    test_pos_rate : pd.Series, defaults to None
        Calculated test positive rates for use in survival calculation of tp_rate
    prevalence_value : int or float, defaults to None
        Prevalence value used for calculation of tp_rate
    time : int or float, defaults to None
        Time of interest in years, used in Survival DCA
    time_to_outcome_col : str, defaults to None
        Column name of time of interest in risks_df
    Returns
    -------
    pd.Series
               
    """
    # Survival
    if time_to_outcome_col is not None:

        risk_rate_among_test_pos = \
            _calc_risk_rate_among_test_pos(
                risks_df=risks_df,
                outcome=outcome,
                model=model,
                thresholds=thresholds,
                time_to_outcome_col=time_to_outcome_col,
                time=time
            )
        tp_rate = risk_rate_among_test_pos * test_pos_rate
    # Binary
    elif time_to_outcome_col is None:
        true_outcome = risks_df[risks_df[outcome] == True][[model]]
        tp_rate = []
        for threshold in thresholds:
            true_tf_above_thresh_dict = dict(pd.Series(true_outcome[model] >= threshold).value_counts())
            if True not in true_tf_above_thresh_dict:
                tp_rate.append(0 / len(true_outcome[model]) * prevalence_value)
            elif True in true_tf_above_thresh_dict:
                tp_rate.append(true_tf_above_thresh_dict[True] / len(true_outcome[model]) * prevalence_value)

    return pd.Series(tp_rate)


def _calc_fp_rate(
        risks_df: pd.DataFrame,
        thresholds: np.ndarray,
        model: str,
        outcome: str,
        test_pos_rate: Optional[pd.Series] = None,
        prevalence_value: Optional[Union[float, int]] = None,
        time: Optional[Union[float, int]] = None,
        time_to_outcome_col: Optional[str] = None,
) -> pd.Series:
    # Survival
    if time_to_outcome_col is not None:
        risk_rate_among_test_pos = \
            _calc_risk_rate_among_test_pos(
                risks_df=risks_df,
                outcome=outcome,
                model=model,
                thresholds=thresholds,
                time_to_outcome_col=time_to_outcome_col,
                time=time
            )
        fp_rate = (1 - risk_rate_among_test_pos) * test_pos_rate
    # Binary
    elif time_to_outcome_col is None:
        false_outcome = risks_df[risks_df[outcome] == False][[model]]

        fp_rate = []
        for threshold in thresholds:
            try:
                fp_rate.append(pd.Series(false_outcome[model] >= threshold).value_counts()[1] / len(
                    false_outcome[model]) * (1 - prevalence_value))
            except:
                fp_rate.append(0 / len(false_outcome[model]) * (1 - prevalence_value))
    return pd.Series(fp_rate)


@beartype
def _calc_initial_stats(
        initial_df: pd.DataFrame,
        risks_df: pd.DataFrame,
        thresholds: np.ndarray,
        outcome: str,
        prevalence_value: Union[float, int],
        time: Optional[Union[float, int]] = None,
        time_to_outcome_col: Optional[str] = None
) -> pd.DataFrame:
    for model in initial_df['model'].value_counts().index:
        test_pos_rate = _calc_test_pos_rate(risks_df=risks_df,
                                            thresholds=thresholds,
                                            model=model)
        tp_rate = \
            _calc_tp_rate(
                risks_df=risks_df,
                thresholds=thresholds,
                model=model,
                outcome=outcome,
                time=time,
                time_to_outcome_col=time_to_outcome_col,
                test_pos_rate=test_pos_rate,
                prevalence_value=prevalence_value
            )

        fp_rate = \
            _calc_fp_rate(
                risks_df=risks_df,
                thresholds=thresholds,
                model=model,
                outcome=outcome,
                time=time,
                time_to_outcome_col=time_to_outcome_col,
                test_pos_rate=test_pos_rate,
                prevalence_value=prevalence_value
            )

        initial_df.loc[initial_df['model'] == model, 'test_pos_rate'] = test_pos_rate.tolist()
        initial_df.loc[initial_df['model'] == model, 'tp_rate'] = tp_rate.tolist()
        initial_df.loc[initial_df['model'] == model, 'fp_rate'] = fp_rate.tolist()

    return initial_df


@beartype
def _calc_more_stats(
        initial_stats_df: pd.DataFrame,
        nper: Optional[int] = 1
):
    initial_stats_df['net_benefit'] = initial_stats_df['tp_rate'] - initial_stats_df['threshold'] / (
            1 - initial_stats_df['threshold']) * initial_stats_df['fp_rate'] - initial_stats_df['harm']

    # A step to calc 'net_intervention_avoided', can drop 'net_benefit_all' column after 'net_intervention_avoided'
    initial_stats_df['net_benefit_all'] = \
        initial_stats_df[initial_stats_df.model == 'all'][
            'net_benefit'].tolist() * len(initial_stats_df['model'].value_counts())

    initial_stats_df['net_intervention_avoided'] = (initial_stats_df.net_benefit - initial_stats_df.net_benefit_all) / \
                                                   (initial_stats_df.threshold / (
                                                               1 - initial_stats_df.threshold)) * nper

    # Drop 'net_benefit_all', as mentioned above
    initial_stats_df = initial_stats_df.drop(columns='net_benefit_all')

    # initial_stats_df['neg_rate'] = 1 - initial_stats_df['prevalence']
    # initial_stats_df['fn_rate'] = initial_stats_df['prevalence'] - initial_stats_df['tp_rate']
    # initial_stats_df['tn_rate'] = initial_stats_df['neg_rate'] - initial_stats_df['fp_rate']
    #
    #
    # initial_stats_df['test_neg_rate'] = initial_stats_df['fn_rate'] + initial_stats_df['tn_rate']
    # initial_stats_df['ppv'] = initial_stats_df['tp_rate'] /\
    #                               (initial_stats_df['tp_rate'] + initial_stats_df['fp_rate'])
    # initial_stats_df['npv'] = initial_stats_df['tn_rate'] /\
    #                               (initial_stats_df['tn_rate'] + initial_stats_df['fn_rate'])
    # initial_stats_df['sens'] = initial_stats_df['tp_rate'] /\
    #                                (initial_stats_df['tp_rate'] + initial_stats_df['fn_rate'])
    # initial_stats_df['spec'] = initial_stats_df['tn_rate'] /\
    #                                (initial_stats_df['tn_rate'] + initial_stats_df['fp_rate'])
    # initial_stats_df['lr_pos'] = initial_stats_df['sens'] /\
    #                                  (1 - initial_stats_df['spec'])
    # initial_stats_df['lr_neg'] = (1 - initial_stats_df['sens']) /\
    #                                  initial_stats_df['spec']

    final_dca_df = initial_stats_df

    return final_dca_df


@beartype
def dca(
        data: pd.DataFrame,
        outcome: str,
        modelnames: list,
        thresholds: np.ndarray = np.arange(0.00, 1.00, 0.01),
        harm: Optional[dict] = None,
        models_to_prob: Optional[list] = None,
        prevalence: Optional[Union[float, int]] = None,
        time: Optional[Union[float, int]] = None,
        time_to_outcome_col: Optional[str] = None,
        nper: Optional[int] = 1
) -> pd.DataFrame:
    risks_df = \
        _create_risks_df(
            data=data,
            outcome=outcome,
            models_to_prob=models_to_prob,
            time=time,
            time_to_outcome_col=time_to_outcome_col
        )

    rectified_risks_df = \
        _rectify_model_risk_boundaries(
            risks_df=risks_df,
            modelnames=modelnames
        )

    prevalence_value = \
        _calc_prevalence(
            risks_df=rectified_risks_df,
            outcome=outcome,
            prevalence=prevalence,
            time=time,
            time_to_outcome_col=time_to_outcome_col
        )

    initial_df = \
        _create_initial_df(
            thresholds=thresholds,
            modelnames=modelnames,
            input_df_rownum=len(rectified_risks_df.index),
            prevalence_value=prevalence_value,
            harm=harm
        )

    initial_stats_df = \
        _calc_initial_stats(
            initial_df=initial_df,
            risks_df=rectified_risks_df,
            thresholds=thresholds,
            outcome=outcome,
            prevalence_value=prevalence_value,
            time=time,
            time_to_outcome_col=time_to_outcome_col
        )

    final_dca_df = \
        _calc_more_stats(
            initial_stats_df=initial_stats_df,
            nper=nper
        )

    return final_dca_df
