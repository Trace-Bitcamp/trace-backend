import xgboost as xgb
import numpy as np
import sys
import pandas as pd
from model.extract_features import get_features
import base64
import cv2

BLUR_RADIUS = 5

class PD_Model:
    def __init__(self):
        self.model = self.load_model()

    def load_model(self):

        model = xgb.Booster()
        model.load_model('model/xgboost_model.json')

        # Feature names: 
        # 'AGE', 'RMS', 'MAX_BETWEEN_ET_HT', 'MIN_BETWEEN_ET_HT', 'STD_DEVIATION_ET_HT', 'MRT', 
        # 'MAX_HT', 'MIN_HT', 'STD_HT', 'CHANGES_FROM_NEGATIVE_TO_POSITIVE_BETWEEN_ET_HT'

        # importance = model.get_score(importance_type='gain')

        # print("Feature importance:", sorted(importance.items(), key=lambda item: item[1], reverse=True))

        return model

    def run_inference(self, traced, template, age):
        print("Running inference...")

        ft_df = pd.DataFrame(get_features(traced, template), index=[0])
        ft_df.insert(0, 'AGE', age)  # Insert 'AGE' as the first column

        return self.model.predict(xgb.DMatrix(ft_df)), ft_df


if __name__ == "__main__":
    model = PD_Model()

    input_df = pd.DataFrame({
        'AGE': 28,
        'RMS': 2446.759108,
        'MAX_BETWEEN_ET_HT': 5388.771096,
        'MIN_BETWEEN_ET_HT': 33435.39545,
        'STD_DEVIATION_ET_HT': 0.0,
        'MRT': 26.849731,
        'MAX_HT': 183.854351,
        'MIN_HT': 0.017068,
        'STD_HT': 1779.550502,
        'CHANGES_FROM_NEGATIVE_TO_POSITIVE_BETWEEN_ET_HT': 0.216138
    }, index=[0])

    predictions = model.model.predict(xgb.DMatrix(input_df))
    print("Predictions:", predictions)

