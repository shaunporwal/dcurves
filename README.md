# dcurves
Diagnostic and prognostic models are typically evaluated with measures of accuracy that do not address clinical
consequences. Decision-analytic techniques allow assessment of clinical outcomes, but often require collection of
additional information that may be cumbersome to apply to models that yield a continuous result. Decision Curve
Analysis is a method for evaluating and comparing prediction models that incorporates clinical consequences,
requiring only the data set on which the models are tested, and can be applied to models that have either continuous or
dichotomous results. The dca function performs decision curve analysis for binary and survival outcomes. Review the
DCA tutorial (towards the bottom) for a detailed walk-through of various applications. Also, see
www.decisioncurveanalysis.org for more information.

#### Installation

###### Use the package manager [pip](https://pip.pypa.io/en/stable/) to install dcurves.

```bash
pip install dcurves
```
###### Import dcurves and numpy
```python
from dcurves import dca, plot_graphs, load_test_data
import numpy as np
```
##### Usage - Binary
```python
from dcurves import dca, plot_graphs, load_test_data
import numpy as np

dca_results = \
    dca(
        data=load_test_data.load_binary_df(),
        outcome='cancer',
        modelnames=['famhistory'],
        thresholds=np.arange(0, 0.45, 0.01)
    )

plot_graphs(
    plot_df=dca_results,
    graph_type='net_benefit',
    y_limits=[-0.05, 0.15],
    color_names=['blue', 'red', 'green']
)
```
##### Usage - Survival
```python
from dcurves import dca, plot_graphs, load_test_data
import numpy as np

dca_results = \
    dca(
        data=load_test_data.load_survival_df(),
        outcome='cancer',
        modelnames=['famhistory', 'marker', 'cancerpredmarker'],
        models_to_prob=['marker'],
        thresholds=np.arange(0, 0.45, 0.01),
        time_to_outcome_col='ttcancer',
        time=1
    )

plot_graphs(
    plot_df=dca_results,
    graph_type='net_benefit',
    y_limits=[-0.025, 0.175],
    color_names=['blue', 'red', 'green', 'purple', 'black']
)
```
#### In-depth tutorial and explanations:
###### https://www.danieldsjoberg.com/dca-tutorial/dca-tutorial-r.html
###### NOTE: Please wait for python snippets to be updated (Coming Extremely Soon!)

#### Contributing
######Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

######Please make sure to update tests as appropriate.

#### License
[Apache 2.0]([https://choosealicense.com/licenses/apache-2.0/])
