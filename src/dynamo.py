""" Module containts functionality to load a DynamoDB table, locally or in AWS
"""

import os


def load_table(dynamo_resource, table_name, logger):
    """Summary: Loads a reference to a DynamoDB table


    Parameters:
        dynamo_resource (DynamoDB.ServiceResource): the DynamoDB reference to load the table from
        table_name (str): the name of the table to load
        logger (aws_lambda_powertools.Logger): the logging object to log events


    Returns:
        DynamoDB.Table: A reference to the table to read & write to
    """

    logger.info(f"Attempting to create table {table_name}")

    if os.environ.get("ENV", "DEV") != "DEV":
        return dynamo_resource.Table(table_name)

    if not table_name:
        logger.debug("No table name provided")
        return None

    available_tables = dynamo_resource.tables.all()

    for table in available_tables:
        if table.table_name == table_name:
            logger.info(f"Table {table_name} already created")
            return dynamo_resource.Table(table_name)

    table = dynamo_resource.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    logger.info(f"Table {table_name} successfully created")
    return table
