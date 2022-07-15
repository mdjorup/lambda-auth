"""Module app contains the event handling logic for a user authentication API
using AWS lambda and AWS KMS
"""


import os
import crypt


from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.event_handler.exceptions import NotFoundError
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.middleware_factory import lambda_handler_decorator

from src.utils import build_response, strong_password


tracer = Tracer()

logger = Logger(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    service=os.environ.get("POWERTOOLS_SERVICE_NAME", "lambda_auth"),
)
# Logging options: info, debug, error, warning

app = APIGatewayRestResolver()


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


@app.post("/register/<username>")
@tracer.capture_method
def register(username):
    logger.append_keys(username=username)
    logger.info("Register Attempted")

    password = app.current_event.json_body.get("password", "")

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

    return build_response(
        200,
        {
            "message": f"Successfully registered user {username}",
            "jwt": "23u8r9qjr239rj12931j21239ej1239e",
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
