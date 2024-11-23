import datetime
import time

import numpy as np
import pandas as pd
from logorator import Logger

from cacharator.cacherator import JSONCache, Cached


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


class BigClass(JSONCache):
    def __init__(self):
        JSONCache.__init__(self, data_id="BIG_1")
        self.name = "BIG"

    @Cached(clear_cache=True)
    @Logger(mode="short")
    def calculation(self, x=2, y=10):
        time.sleep(0.5)
        return x ** y

    def long_calc(self, n=10):
        result = []
        for i in range(1, n):
            for j in range(1, n):
                result.append(self.calculation(i, j))
        return result

bc = BigClass()
#print(bc.list_wrapped_methods(wrapper_attribute="clear_cache"))
print(bc.calculation(x=9))
print(bc.calculation(x=10))
print(bc.calculation(x=9))
print(bc.calculation(x=10))

# Usage

#obj = MyClass()
#print(len(obj.long_calc(n=5)))
#print(obj.panda())
