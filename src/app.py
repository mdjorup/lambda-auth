"""Module app contains the event handling logic for a user authentication API
using AWS lambda and AWS KMS
"""

import os
import crypt
from hmac import compare_digest as compare_hash

from boto3 import resource
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.event_handler.exceptions import NotFoundError
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.middleware_factory import lambda_handler_decorator
import jwt

from src.utils import build_response, strong_password, generate_jwt
from src.dynamo import load_table


tracer = Tracer()

logger = Logger(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    service=os.environ.get("POWERTOOLS_SERVICE_NAME", "lambda_auth"),
)
# Logging options: info, debug, error, warning

app = APIGatewayRestResolver()

dynamodb = resource(
    "dynamodb",
    endpoint_url=os.environ.get("DB_ENDPOINT_URL", "http://host.docker.internal:8000"),
)

TABLE = os.environ.get("DB_NAME")


@app.exception_handler(Exception)
@tracer.capture_method
def handle_uncaught_error(ex: Exception):
    """Summary:


    Parameters:


    Returns:

    """
    logger.exception(msg=str(ex))

    return build_response(
        500, {"message": "There was an uncaught error", "error": str(ex)}
    )


@app.not_found
@tracer.capture_method
def handle_not_found(ex: NotFoundError):
    """Summary:
        Handles requests that route to endpoints that are not found

    Parameters:
        ex (aws_lambda_powertools.event_handler.exceptions.NotFoundError): The not found error

    Returns:
        aws_lambda_powertools.event_handler.api_gateway.Response
    """
    method = app.current_event.http_method
    path = app.current_event.path
    logger.warning(f"Route {method} {path} not found")
    return build_response(
        404,
        {
            "message": f"Route {method} {path} not found",
            "error": f"NotFoundError {str(ex)}",
        },
    )


@app.get("/health")
def health():
    """Summary:
        Gets the health of the API

    Returns:
        aws_lambda_powertools.event_handler.api_gateway.Response: 200 OK if healthy
    """
    return build_response(200, {"message": "healthy"})


@app.get("/users")
@tracer.capture_method
def users():
    """Summary:
        Gets all users and encrypted passwords stored in the database

    Returns:
        aws_lambda_powertools.event_handler.api_gateway.Response:
            200 OK with a list of all users
    """

    logger.info("GET users attempted")

    table = load_table(dynamodb, TABLE, logger)

    response = table.scan()
    data = response.get("Items")

    logger.info("Successful GET users")

    return build_response(200, data)


@app.post("/register/<username>")
@tracer.capture_method
def register(username):
    """Summary:
        Registers a new user by adding it to the database and creates a new JWT

    Parameters:
        username (str): The username to register with

    Returns:
        aws_lambda_powertools.event_handler.api_gateway.Response:
            201 if user is successfully registered
            400 if no password provided or weak password
            409 if username already exists in DB
            500 if there is a error accessing the table

    """
    logger.append_keys(username=username)
    logger.info("POST register Attempted")

    password = app.current_event.json_body.get("password", "")

    table = load_table(dynamodb, TABLE, logger)

    if not table:
        return build_response(
            500,
            {
                "message": f"Problem loading table {TABLE}",
                "error": "Unable to load table",
            },
        )

    existing_user = table.get_item(Key={"username": username})

    if existing_user.get("Item"):
        logger.debug(f"User {username} already exists")
        return build_response(
            409,
            {
                "message": "Please pick a different username",
                "error": "Username already taken",
            },
        )

    if not password:
        logger.debug("Invalid request body - please provide a password")
        return build_response(
            400,
            {"message": "Please provide a password", "error": "Invalid request body"},
        )

    if not strong_password(password):
        logger.debug("Weak Password")
        return build_response(
            400,
            {"message": "Please provide a stronger password", "error": "Weak password"},
        )

    encrypted_pw = crypt.crypt(password)

    item = {"username": username, "password": encrypted_pw}

    table.put_item(Item=item)

    logger.info(f"Successfully added user <{username}> to table <{TABLE}>")

    # create jwt

    token = generate_jwt(username)

    logger.info(f"User <{username}> successfully registerd")

    return build_response(
        201,
        {
            "username": username,
            "table": TABLE,
            "message": f"Successfully registered user <{username}>",
            "jwt": token,
        },
    )


@app.post("/login/<username>")
@tracer.capture_method
def login(username):
    """Summary:
        Attempts to log an existing user in

    Parameters:
        username (str): The username of the user to log in

    Returns:
        aws_lambda_powertools.event_handler.api_gateway.Response:
            200 if user is successfully logs in with a JWT
            400 if no password provided in request body
            401 if the password provided is incorrect
            409 if the user does not exist in the database
            500 if there is an issue referencing the the database
    """
    logger.append_keys(username=username)

    logger.info("POST login Attempted")

    password = app.current_event.json_body.get("password", "")

    table = load_table(dynamodb, TABLE, logger)

    if not table:
        return build_response(
            500,
            {
                "message": f"Problem loading table {TABLE}",
                "error": "Unable to load table",
            },
        )

    existing_user = table.get_item(Key={"username": username}).get("Item")

    if not existing_user:
        logger.debug(f"User {username} does not exists")
        return build_response(
            409,
            {
                "message": "Please register instead",
                "error": "Username does not exist",
            },
        )

    if not password:
        logger.debug("Invalid request body - please provide a password")
        return build_response(
            400,
            {"message": "Please provide a password", "error": "Invalid request body"},
        )

    encrypted_pw = existing_user.get("password")

    if not compare_hash(encrypted_pw, crypt.crypt(password, encrypted_pw)):
        logger.debug("Incorrect password")
        return build_response(
            401, {"message": "Incorrect password", "error": "Passwords do not match"}
        )

    token = generate_jwt(username)

    logger.info(f"User <{username}> successfully logged in")

    return build_response(
        200,
        {
            "username": username,
            "table": TABLE,
            "message": f"Successfully logged in user <{username}>",
            "jwt": token,
        },
    )


@app.put("/validate")
@tracer.capture_method
def validate():
    """Summary:
        Checks to see if a JWT is valid

    Returns:
        aws_lambda_powertools.event_handler.api_gateway.Response:
            200 if JWT is valid
            400 if no jwt provided in the request body
            401 if the token is invalid or expired
    """

    logger.info("Attempting to validate jwt")

    token = app.current_event.json_body.get("jwt")

    if not token:
        logger.debug("Invalid request body - please provide a jwt")
        return build_response(
            400,
            {"message": "Please provide a jwt", "error": "Invalid request body"},
        )

    secret = os.environ.get("JWT_SECRET")

    try:
        jwt.decode(token, secret, algorithms=["HS256"])
        logger.info("Successfully validated jwt")
        return build_response(200, {"message": "Successfully validated jwt"})
    except jwt.exceptions.ExpiredSignatureError as ex:
        logger.debug("Token expired")
        return build_response(401, {"message": "Token Expired", "error": str(ex)})
    except jwt.exceptions.InvalidTokenError as ex:
        logger.debug("Invalid token")
        return build_response(
            401, {"message": "Invalid token. Please log in again.", "error": str(ex)}
        )


@lambda_handler_decorator
def middleware(event_handler, event, context):
    """Summary:
        Contains the middleware functionality to process requests before and after resolved

    Parameters:
        event_handler (function): the lambda handler to resolve events
        event (dict): Information about the specific request
        context (aws_lambda_powertools.utilities.typing.LambdaContext):
            Additional information about the context of the request

    Returns:
        dict: The response obtained by executing the middleware and event handler
    """

    # BEFORE

    event["authorized"] = True

    # HANDLER
    response = event_handler(event, context)

    # AFTER
    return response


@middleware
@logger.inject_lambda_context(
    log_event=os.environ.get("LOG_EVENT", True),
    correlation_id_path=correlation_paths.API_GATEWAY_REST,
)
@tracer.capture_lambda_handler
def handler(event: dict = None, context: LambdaContext = LambdaContext()):
    """Summary:
        The event handler for the lambda function

    Parameters:
        event (dict): Information about the specific request
        context (aws_lambda_powertools.utilities.typing.LambdaContext):
            Additional information about the context of the request

    Returns:
        dict: A HTTP response based on the request
    """

    logger.append_keys(
        path=event.get("path"),
        method=event.get("httpMethod"),
        origin_ip=event.get("requestContext", {})
        .get("identity", {})
        .get("sourceIp", "UNAVAILABLE"),
    )

    if not event.get("authorized", True):
        return build_response(401, {"message": "Unauthorized"})

    return app.resolve(event, context)
