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
from common_utilities.utilities import verify_expected_result_as_file_to_actual_result_as_database_table, \
verify_expected_result_as_database_to_actual_result_as_database_table

from config.etl_configuration import *

logging.basicConfig(
    filename="logs/etl_process.log",
    filemode='a',
    format='%(asctime)s-%(levelname)s-%(message)s',
    level =logging.INFO
)
logger = logging.getLogger(__name__)

class TestDataLoading:

    def test_data_loading_monthly_sales_summary(self, connect_to_mysql_database):
        try:
            test_case_name = inspect.currentframe().f_code.co_name
            expected_query = """select product_id,year,month,total_sales from monthly_sales_summary_source where month =10 order by product_id"""
            actual_query = """select product_id,year,month,total_sales from monthly_sales_summary where month =10 order by product_id"""
            verify_expected_result_as_database_to_actual_result_as_database_table(test_case_name,expected_query,connect_to_mysql_database,actual_query,connect_to_mysql_database)
        except Exception as e:
            logger.error(f"error while sales data loading checks..{e}")

            raise

