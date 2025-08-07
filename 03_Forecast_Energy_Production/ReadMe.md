# Forecasting Energy Production

A time series forecasting project to predict energy production up to 6 hours in advance using an LSTM neural network.

Please see my notes within the notebooks I did not find time to provide a more detailed overview here. But the highlights are that I chose to validate and test using the start rather than the end of the dataset as this avoided out of training set scenarios. There is a trade of here of course. 

The final model chosen after some tweaking is a single layer LSTM model with 64 hidden layers, Batch normalization and a Two-layer fully connected neural/dense network as a final layer. I also made use of weight initialisation.

This was my first time using an LSTM model!

The project is split into 4 notebooks:

1. **Exploratory Data Analysis**: Initial data exploration, cleaning and insights including visualizations of the relationships between weather variables and power output.

2. **Feature Engineering**: Creation of features including:
   - Wind shear and wind component calculations
   - Rolling averages and rates of change
   - Time based features (time of day)
   - Lag features for all variables

3. **Build and Train Model**: Implementation of an LSTM model in PyTorch with:
   - Custom dataset class for multi-horizon forecasting
   - Batched training with early stopping
   - Hyperparameter optimization
   - Model evaluation across different forecast horizons

4. **Model Evaluation**: Detailed evaluation of model performance including:
   - Error metrics by forecast horizon
   - Visualization of predictions vs actuals

## Requirements

Install requirements using:

```bash
pip install -r requirements.txt
```

## Key Findings

- Model achieves MAE of ~1100kW across all forecast horizons
- Performance degrades only slightly with increasing forecast horizon
- Model struggles most with:
  - Rapid changes in wind conditions
  - Extreme high/low power output scenarios
  - Curtailment scenarios
- Simple post-processing by clipping predictions to [0, 5500] range improves performance

## Future Improvements

- Incorporate turbine status/curtailment data
- Predict available power rather than utilised power, to avoid difficulty handling curtailment
- Experiment with alternative architectures (transformers, temporal fusion transformers)
