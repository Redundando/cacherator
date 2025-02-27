import datetime
import time
import inspect
import numpy as np
import pandas as pd
from logorator import Logger

from cacherator.cacherator import JSONCache, Cached


class MyClass:

    def __init__(self):
        #self.data_id = "Jupiter"
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
        JSONCache.__init__(self)
        self.name = "BIG"


    @Cached()
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

    @property
    @Cached()
    def num_info(self):
        print("CALLING")
        return 555

bc = BigClass()
#bc.kl = 99
#self_vars = {
#    k: v for k, v in vars(bc).items()
#    if not isinstance(getattr(type(bc), k, None), property)
#}

print(bc._cached_variables)


# Usage

#obj = MyClass()
#print(len(obj.long_calc(n=5)))
#print(obj.panda())
