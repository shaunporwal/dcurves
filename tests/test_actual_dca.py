

def test_actual_dca1():
    from dcurves import dca, plot_graphs, load_test_data
    import numpy as np

    dca_results = \
        dca(
            data=load_test_data.load_binary_df(),
            outcome='cancer',
            modelnames=['famhistory'],
            thresholds=[i/100 for i in range(0, 46)]
        )

    # plot_graphs(
    #     plot_df=dca_results,
    #     graph_type='net_benefit',
    #     y_limits=[-0.05, 0.15],
    #     color_names=['blue', 'red', 'green']
    # )

def test_actual_dca2():
    from dcurves import dca, plot_graphs, load_test_data
    import numpy as np

    # print('\n', load_test_data.load_survival_df()['ttcancer'].describe())

    dca_results = \
        dca(
            data=load_test_data.load_survival_df(),
            outcome='cancer',
            modelnames=['famhistory', 'marker', 'cancerpredmarker'],
            models_to_prob=['marker'],
            thresholds=[i/100 for i in range(0, 46)],
            time_to_outcome_col='ttcancer',
            time=1
        )

    # plot_graphs(
    #     plot_df=dca_results,
    #     graph_type='net_benefit',
    #     y_limits=[-0.025, 0.175],
    #     color_names=['blue', 'red', 'green', 'purple', 'black']
    # )