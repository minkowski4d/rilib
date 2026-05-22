from typing import List
import pandas as pd
import numpy as np
from .db_connection import run_query 
import scipy.stats as stats
class Hypothesis:
    def __init__(self, 
                 name: str, 
                 target_column: str, 
                 level: str = 'user', 
                 where: str = None, 
                 sample_size_calc = None, 
                 conversions_calc = None,
                 metric_type = 'ratio'):
        self.name = name
        self.target_column = target_column
        self.level = level
        self.where = where
        self.metric_type = metric_type
        
        self.sample_size_calc = sample_size_calc if sample_size_calc else lambda df: len(df) 
        self.conversions_calc = conversions_calc if conversions_calc else lambda df: sum(df[self.target_column])
        
    def sample_size(self, df):
        return self.sample_size_calc(df)
    
    def conversions(self, df):
        return self.conversions_calc(df)
    
class Experiment:
    def __init__(self, start_date: str, end_date: str, post_conversion_days: int):
        self.start_date = start_date
        self.end_date = end_date
        self.post_conversion_days = post_conversion_days
        
        self.hypotheses = dict()
        
        self.query = None
        self.data = None
    
    def add_hypothesis(self, hypothesis: Hypothesis):
        self.hypotheses[hypothesis.name] = hypothesis
    
    def add_hypotheses(self, hypotheses: List[Hypothesis]):
        for each in hypotheses:
            self.add_hypothesis(each)
    
    def add_query(self,query: str):
        self.query = query.format(start_date = self.start_date, end_date = self.end_date, conversion_days = self.post_conversion_days)
    
    def load_data(self):
        self.data = run_query(self.query)
    
    @staticmethod
    def make_metrics(hyp: Hypothesis, df: pd.DataFrame()):
        sample_size = hyp.sample_size(df)
        conversions = hyp.conversions(df)
        cr = conversions / sample_size
        table = np.append(np.ones(conversions),np.zeros(sample_size - conversions))
        return sample_size, conversions, cr, table
        
    def generate_results(self):
        results = list()
        cols = list()
        
        for hyp_name,hyp in self.hypotheses.items():
            data = self.data.query(hyp.where) if hyp.where else self.data

            control = data.query('experiment_condition == "0"')
            variant = data.query('experiment_condition == "1"')
            
            c_sample_size, c_conversions, c_cr, c_table = self.make_metrics(hyp,control)
            v_sample_size, v_conversions, v_cr, v_table = self.make_metrics(hyp,variant)
            
            if hyp.metric_type == 'ratio':
                pval = stats.ttest_ind(c_table,v_table)[1]
            else:
                pval = stats.ttest_ind(control[hyp.target_column],variant[hyp.target_column])[1]

            values = { 
                'total_sample_size': c_sample_size + v_sample_size,
                'control_sample_size': c_sample_size,
                'control_conversions': c_conversions,
                'control_conversion_rate': c_cr,
                'variant_sample_size': v_sample_size,
                'variant_conversions': v_conversions,
                'variant_conversion_rate': v_cr,
                'improvement': "{:.2%}".format(1-(c_cr/v_cr)),
                'p-value': pval
            }
            
            results.append(values)
            cols.append(hyp_name)
            
        output = (pd.DataFrame(results, index = cols)
                       .astype(object)
                       .T)
        return output 
