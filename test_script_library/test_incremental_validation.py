import pandas as pd
from sqlalchemy import create_engine
import cx_Oracle
import logging
import oracledb
import os
import sys
import pytest
import inspect

# logging configuration
from common_utilities.utilities import verify_expected_result_as_file_to_actual_result_as_database_table,get_incremental_target_records, \
    validate_new_records,validate_updated_records
from config.etl_configuration import *

logging.basicConfig(
    filename="logs/etl_process.log",
    filemode='a',
    format='%(asctime)s-%(levelname)s-%(message)s',
    level =logging.INFO
)
logger = logging.getLogger(__name__)


class TestIncrementalValidation:

    def test_validate_new_records(
            self,
            connect_to_mysql_database):

        execution_start_time = "2026-06-15 00:00:00"

        source_df = pd.read_csv(
            "test_data/expected_incremental_records.csv"
        )

        target_df = get_incremental_target_records(
            connect_to_mysql_database,
            execution_start_time
        )

        missing_records = validate_new_records(
            source_df,
            target_df
        )

        assert len(missing_records) == 0, \
            f"New records missing in target: {missing_records}"

    def test_validate_updated_records(
            self,
            connect_to_mysql_database):
        execution_start_time = "2026-06-15 00:00:00"

        source_df = pd.read_csv(
            "test_data/expected_incremental_records.csv"
        )

        target_df = get_incremental_target_records(
            connect_to_mysql_database,
            execution_start_time
        )

        mismatches = validate_updated_records(
            source_df,
            target_df
        )

        assert len(mismatches) == 0, \
            f"Updated records mismatch found: {mismatches}"