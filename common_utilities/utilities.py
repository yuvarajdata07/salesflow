import pandas as pd
from sqlalchemy import create_engine
# import cx_Oracle
import logging
import os
import sys
from sqlalchemy import inspect
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# logging configuration
from config.etl_configuration import *

logging.basicConfig(
    filename="logs/etl_process.log",
    filemode='a',
    format='%(asctime)s-%(levelname)s-%(message)s',
    level =logging.INFO
)
logger = logging.getLogger(__name__)


# database connection
# mysql_conn = create_engine(f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")


def verify_expected_result_as_file_to_actual_result_as_database_table(test_case_name, file_path, file_type,
                                                                      query_actual, db_actual):
    try:
        # 1. Load Expected Data
        if file_type == "csv":
            df_expected = pd.read_csv(file_path)
        elif file_type == "json":
            df_expected = pd.read_json(file_path)
        elif file_type == "xml":
            df_expected = pd.read_xml(file_path, xpath=".//item")
        else:
            raise ValueError(f"Unsupported file format: {file_type}")

        # 2. Load Actual Data
        df_actual = pd.read_sql(query_actual, db_actual)

        # 3. Data Cleanup (Crucial for successful matching)
        # Ensure column order and types match
        df_actual = df_actual[df_expected.columns]

        # 4. Identify Differences
        os.makedirs("differences", exist_ok=True)

        # Using merge with indicator to find mismatched rows
        comparison_df = pd.merge(df_expected, df_actual, how='outer', indicator=True)

        extra_in_expected = comparison_df[comparison_df['_merge'] == 'left_only'].drop('_merge', axis=1)
        extra_in_actual = comparison_df[comparison_df['_merge'] == 'right_only'].drop('_merge', axis=1)

        # 5. Check for Extra Rows and Save
        errors = []

        if not extra_in_expected.empty:
            path = f"differences/extra_in_expected_{test_case_name}.csv"
            extra_in_expected.to_csv(path, index=False)
            msg = f"FAILURE: {len(extra_in_expected)} rows found in FILE but missing in DB."
            logger.error(msg)
            errors.append(msg)

        if not extra_in_actual.empty:
            path = f"differences/extra_in_actual_{test_case_name}.csv"
            extra_in_actual.to_csv(path, index=False)
            msg = f"FAILURE: {len(extra_in_actual)} rows found in DB but missing in FILE."
            logger.error(msg)
            errors.append(msg)

        # 6. Final Strict Assertion
        if errors:
            # Joining all error messages into one big failure string
            error_report = "\n".join(errors)
            raise AssertionError(f"Test Failed for {test_case_name}:\n{error_report}")

        # Only if the 'errors' list is empty will it reach here
        logger.info(f"Test {test_case_name} passed successfully.")

    except Exception as e:
        # We still log the error, but we must ensure it's raised so the runner sees it
        logger.error(f"Critical Error in {test_case_name}: {str(e)}")
        raise

def verify_expected_result_as_database_to_actual_result_as_database_table(test_case_name, query_expected, db_expected,
                                                                      query_actual, db_actual):
    try:
        # 1. Load Expected Data
        df_expected = pd.read_sql(query_expected, db_expected)
        logger.info(f"Expected data in the file is: {df_expected}")

        # 2. Load Actual Data
        df_actual = pd.read_sql(query_actual, db_actual)
        logger.info(f"Actual data in the file is: {df_actual}")

        # 3. Data Cleanup (Crucial for successful matching)
        # Ensure column order and types match
        df_actual = df_actual[df_expected.columns]

        # 4. Identify Differences
        os.makedirs("differences", exist_ok=True)

        # Using merge with indicator to find mismatched rows
        comparison_df = pd.merge(df_expected, df_actual, how='outer', indicator=True)

        extra_in_expected = comparison_df[comparison_df['_merge'] == 'left_only'].drop('_merge', axis=1)
        extra_in_actual = comparison_df[comparison_df['_merge'] == 'right_only'].drop('_merge', axis=1)

        # 5. Save differences if they exist
        if not extra_in_expected.empty:
            extra_in_expected.to_csv(f"differences/extra_in_expected_{test_case_name}.csv", index=False)
            logger.warning(f"{test_case_name}: Found {len(extra_in_expected)} rows in file but not in DB.")

        if not extra_in_actual.empty:
            extra_in_actual.to_csv(f"differences/extra_in_actual_{test_case_name}.csv", index=False)
            logger.warning(f"{test_case_name}: Found {len(extra_in_actual)} rows in DB but not in file.")

        # 6. Final Assertion
        assert df_actual.equals(df_expected), f"Data mismatch in {test_case_name}. See 'differences' folder."
        logger.info(f"Test {test_case_name} passed successfully.")

    except Exception as e:
        logger.error(f"Error in {test_case_name}: {str(e)}")
        raise e


# Utiliies for for table existence check
def database_tables_exists(db_conn, expected_table_list, db_name):
    query = f"""select TABLE_NAME FROM information_schema.tables where table_schema ='{db_name}'"""

    df = pd.read_sql(query, db_conn)
    actual_table_list = df['TABLE_NAME'].tolist()
    logger.info(f"the actual tables are :{actual_table_list}")
    missing_table_list = []
    for tbl in expected_table_list:
        if tbl not in actual_table_list:
            missing_table_list.append(tbl)
    return missing_table_list

# Utiliies for test_data_types_of_columns_in_the_table_name

def get_actual_table_schema(connection, table_name, schema_name):
    inspector = inspect(connection)
    columns = inspector.get_columns(table_name, schema=schema_name)

    actual_schema = {}
    for col in columns:
        db_type = str(col['type']).lower()
        col_name = col['name']

        # Normalization Logic
        if "int" in db_type:
            actual_schema[col_name] = "int"
        elif "decimal(10,2)" in db_type:
            # This captures the exact string like 'decimal(10,2)'
            actual_schema[col_name] = "decimal(10,2)"
        elif "date" in db_type:
            actual_schema[col_name] = "date"
        elif "timestamp" in db_type or "datetime" in db_type:
            actual_schema[col_name] = "timestamp"
        else:
            actual_schema[col_name] = db_type

    return actual_schema


# data quality checks related utility fucntions
def check_for_duplicates_for_specific_column_in_file(file_path, file_type, column_name):
    try:
        if file_type == "csv":
            df = pd.read_csv(file_path)
        elif file_type == "json":
            df = pd.read_json(file_path)
        elif file_type == "xml":
            df = pd.read_xml(file_path, xpath=".//item")
        else:
            raise ValueError(f"unsupported file format passed{file_path}")
        logger.info(f"The data in the file is : {df}")

        if df[column_name].duplicated().any() == True:
            return False
        else:
            return True
    except Exception as e:
        logger.error(f" error occured while pefroming duplicate checks..")

def check_for_duplicates_across_the_file(file_path, file_type):
    try:
        if file_type == "csv":
            df = pd.read_csv(file_path)
        elif file_type == "json":
            df = pd.read_json(file_path)
        elif file_type == "xml":
            df = pd.read_xml(file_path, xpath=".//item")
        else:
            raise ValueError(f"unsupported file format passed{file_path}")
        logger.info(f"The data in the file is : {df}")

        if df.duplicated().any() == True:
            return False
        else:
            return True
    except Exception as e:
        logger.error(f" error occured while pefroming duplicate checks..")


def get_duplicate_counts_by_column(connection, table_name, schema_name, column_name):
    """
    Returns a list of tuples (value, count) for any value that appears
    more than once in the specified column.
    """
    query = text(f"""
        SELECT {column_name}, COUNT(*) as duplicate_count
        FROM {schema_name}.{table_name}
        GROUP BY {column_name}
        HAVING COUNT(*) > 1
    """)

    result = connection.execute(query).fetchall()
    # Returns list of Row objects, e.g., [(101, 5), (102, 2)]
    return result

def get_duplicate_row_count(connection, table_name, schema_name):
    """Counts how many rows are exact duplicates of another row."""
    # 1. Fetch the column names for the table
    column_query = text(f"SHOW COLUMNS FROM {schema_name}.{table_name}")
    result = connection.execute(column_query)
    columns = [row[0] for row in result.fetchall()]
    actual_columns_in_table = ", ".join(columns)

    # 2. Use the dynamically generated column list
    query = text(f"""
       SELECT SUM(cnt - 1) FROM (
            SELECT COUNT(*) as cnt 
            FROM {schema_name}.{table_name} 
            GROUP BY {actual_columns_in_table} 
            HAVING COUNT(*) > 1
        ) as dup_set
    """)
    result = connection.execute(query).scalar()
    return result if result else 0

def get_duplicate_pk_details(connection, table_name, schema_name, pk_column):
    """Finds specific IDs that are duplicated and their counts."""
    query = text(f"""
        SELECT {pk_column}, COUNT(*) as occurrences
        FROM {schema_name}.{table_name}
        GROUP BY {pk_column}
        HAVING COUNT(*) > 1
    """)
    return connection.execute(query).fetchall()

# def check_for_duplicates_across_the_table(db_conn, table_name):
#     pass
#
# def check_for_duplicates_for_a_specific_column__the_table(db_conn, table_name, column_name):
#     pass

# Null value ( empty ) checks in the file

def check_for_null_values_for_specific_column_in_file(file_path, file_type, column_name):
    try:
        if file_type == "csv":
            df = pd.read_csv(file_path)
        elif file_type == "json":
            df = pd.read_json(file_path)
        elif file_type == "xml":
            df = pd.read_xml(file_path, xpath=".//item")
        else:
            raise ValueError(f"unsupported file format passed{file_path}")
        logger.info(f"The data in the file is : {df}")

        if df[column_name].isnull().values.any() == True:
            return False
        else:
            return True
    except Exception as e:
        logger.error(f" error occured while pefroming duplicate checks..")


# incremental validation
def get_incremental_target_records(connection, execution_start_time):
    """
    Retrieve records processed in the latest ETL run.
    """

    query = f"""
        SELECT *
        FROM monthly_sales_summary
        WHERE etl_updated_dt >= '{execution_start_time}'
    """

    return pd.read_sql(query, connection)


def validate_new_records(source_df, target_df):
    """
    Validate newly inserted records.
    """
    source_keys = set(source_df["product_id"])
    target_keys = set(target_df["product_id"])

    missing_records = source_keys - target_keys

    return missing_records


def validate_updated_records(source_df, target_df):
    """
    Validate updated records.
    """

    mismatches = []

    merged = source_df.merge(
        target_df,
        on=["product_id", "month", "year"],
        suffixes=("_source", "_target")
    )

    for _, row in merged.iterrows():

        if row["total_sales_source"] != row["total_sales_target"]:

            mismatches.append(
                {
                    "product_id": row["product_id"],
                    "source_sales": row["total_sales_source"],
                    "target_sales": row["total_sales_target"]
                }
            )

    return mismatches