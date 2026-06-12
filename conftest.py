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
from config.etl_configuration import *
from common_utilities.utilities import verify_expected_result_as_file_to_actual_result_as_database_table

logging.basicConfig(
    filename="logs/etl_process.log",
    filemode='a',
    format='%(asctime)s-%(levelname)s-%(message)s',
    level =logging.INFO
)
logger = logging.getLogger(__name__)

@pytest.fixture()
def connect_to_mysql_database():
    logger.info("mysql  database connection is being established..")
    mysql_conn = create_engine(f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}").connect()
    logger.info("mysql database connection has established..")
    yield mysql_conn
    mysql_conn.close()
    logger.info("mysql database connection has been closed..")