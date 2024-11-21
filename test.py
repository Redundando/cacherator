import datetime

import numpy as np
import pandas as pd
from logorator import Logger

from json_cache.json_cache import json_cache


@json_cache(clear_cache=False)
class MyClass:

    def __init__(self):
        self.data_id = "Jupiter"
        self.weight = 77

    def calculation(self, x=2, y=10):
        return x ** y

    @Logger()
    def long_calc(self, n=10):
        result = []
        for i in range(1, n):
            for j in range(1, n):
                result.append(obj.calculation(i, j))
        return result

    def panda(self):
        rows = 10  # Number of rows
        columns = 5  # Number of columns

        # Generate random numbers
        data = np.random.rand(rows, columns)  # Uniformly distributed random numbers between 0 and 1

        # Create the DataFrame
        df = pd.DataFrame(data, columns=[f'Column_{i + 1}' for i in range(columns)])
        return df

    @property
    def timer(self):
        return datetime.datetime.now()


# Usage
obj = MyClass()
print(len(obj.long_calc(n=5)))
print(obj.panda())
