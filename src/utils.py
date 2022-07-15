"""Module utils contains utility functions to be used across the application.
"""
import json
import re

from aws_lambda_powertools.event_handler.api_gateway import Response
from aws_lambda_powertools.event_handler import content_types


def build_response(status_code: int, body):
    """
    Summary:
        Returns a standard response object used throughout the application

    Parameters:
        status_code (int): HTTP status code for the response
        body: Response body

    Returns:
        Response: A response with the given status code and body
    """
    if not isinstance(status_code, int):
        raise TypeError

    return Response(
        status_code=status_code,
        content_type=content_types.APPLICATION_JSON,
        body=json.dumps(body),
    )


def strong_password(password):
    password_pattern = "^(?=.*?[A-Z])(?=.*?[a-z])(?=.*?[0-9])(?=.*?[#?!@$%^&*-]).{8,}$"

    match = re.match(
        password_pattern,
        password,
    )

    if match:
        return True
    else:
        return False
