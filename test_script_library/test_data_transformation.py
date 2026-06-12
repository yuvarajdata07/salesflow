import pandas as pd
from sqlalchemy import create_engine
import cx_Oracle
import logging
import oracledb
import os
import sys
import pytest
import inspect

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# logging configuration
from common_utilities.utilities import verify_expected_result_as_file_to_actual_result_as_database_table
from config.etl_configuration import *

logging.basicConfig(
    filename="logs/etl_process.log",
    filemode='a',
    format='%(asctime)s-%(levelname)s-%(message)s',
    level =logging.INFO
)
logger = logging.getLogger(__name__)


class TestDataTransformation:
    # @pytest.mark.data_transformation
    # @pytest.mark.regression_test
    # @pytest.mark.smoke_test
    def test_data_transformation_filter_sales(self,connect_to_mysql_database):
        try:
            test_case_name = inspect.currentframe().f_code.co_name
            expected_query = """select * from stag_sales where sale_date>='2025-10-01'"""
            actual_query = """select * from filtered_sales where sale_date>='2025-10-01'"""
            verify_expected_result_as_database_to_actual_result_as_database_table(test_case_name,expected_query,connect_to_mysql_database,actual_query,connect_to_mysql_database)
        except Exception as e:
            logger.error(f"error while sales data extraction checks..")


    def test_data_transformation_Aggregator_sales(self, connect_to_mysql_database):
        try:
            test_case_name = inspect.currentframe().f_code.co_name
            expected_query = """select product_id,year(sale_date) as year,month(sale_date) as month,sum(price*quantity) as total_sales  
                        from filtered_sales group by product_id,year(sale_date) ,month(sale_date)"""
            actual_query = """SELECT * FROM sales_reporting.monthly_sales_summary_source where month = 10"""
            verify_expected_result_as_database_to_actual_result_as_database_table(test_case_name,expected_query,connect_to_mysql_database,actual_query,connect_to_mysql_database)
        except Exception as e:
            logger.error(f"error while Aggregator sales transformation checks..")

