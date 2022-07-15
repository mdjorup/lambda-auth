def load_table(dynamo_client, table_name, logger):
    logger.info(f"Attempting to create table {table_name}")

    available_tables = dynamo_client.list_tables().get("TableNames", [])

    if not table_name:
        logger.debug("No table name provided")
        return

    if table_name in available_tables:
        logger.info(f"Table {table_name} already created")
        return

    try:
        dynamo_client.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )
        logger.info(f"Table {table_name} successfully created")
    except Exception as ex:
        logger.debug(f"Error creating table {table_name}. {str(ex)}")
