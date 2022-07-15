"""Module app contains the event handling logic for a user authentication API
using AWS lambda and AWS KMS
"""


import os
import crypt


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
    logger.exception(msg=str(ex))

    return build_response(
        500, {"message": "There was an uncaught error", "error": str(ex)}
    )


@app.not_found
@tracer.capture_method
def handle_not_found(ex: NotFoundError):
    method = app.current_event.http_method
    path = app.current_event.path
    # definitely want the IP address
    logger.warning(f"Route {method} {path} not found")
    return build_response(
        404, {"message": f"Route {method} {path} not found", "error": "NotFoundError"}
    )


@app.get("/health")
def health():

    return build_response(200, {"message": "healthy"})


@app.get("/users")
@tracer.capture_method
def users():

    logger.info("GET users attempted")

    table = load_table(dynamodb, TABLE, logger)

    response = table.scan()
    data = response.get("Items")

    logger.info("Successful GET users")

    return build_response(200, data)


@app.post("/register/<username>")
@tracer.capture_method
def register(username):
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

    return build_response(
        200,
        {
            "message": f"Successfully logged in user {username}",
            "jwt": "23u8r9qjr239rj12931j21239ej1239e",
        },
    )


@app.put("/validate")
@tracer.capture_method
def validate():

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
