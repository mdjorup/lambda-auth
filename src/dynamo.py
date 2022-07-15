def load_table(dynamo_resource, table_name, logger):

    logger.info(f"Attempting to create table {table_name}")

    if not table_name:
        logger.debug("No table name provided")
        return None

    available_tables = dynamo_resource.tables.all()

    for table in available_tables:
        if table.table_name == table_name:
            logger.info(f"Table {table_name} already created")
            return dynamo_resource.Table(table_name)

    try:
        table = dynamo_resource.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )
        logger.info(f"Table {table_name} successfully created")
        return table
    except Exception as ex:
        logger.debug(f"Error creating table {table_name}. {str(ex)}")
        return None
