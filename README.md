# lambda-auth

This repository contains the code to easily set up a user authentication system using AWS Lambda and AWS DynamoDB. This README has instructions on how to set up DynamoDB locally and how to invoke the lambda function locally. The authentication is done through a username and password, and users who successfully log in are issued a JWT.

This system is designed to be as easy as possible! Please feel free to fork this repo to get you started building your own user authentication system using AWS.

# Getting Started

## Prerequisites

If you already have any of these installed, you don't need to reinstall them.

1. Install [Python 3.9](https://www.python.org/downloads/release/python-3913/)
2. Install [Docker Desktop](https://docs.docker.com/desktop/)
   - Install the appropriate version for your OS
3. Install the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
4. Install the [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)

## Environment Setup

1. Fork this repository, then pull it down locally into the project directory of your choice
2. Navigate to the project directory
3. Verify that pip is installed by running `pip --version`
4. Run `pip install --user virtualenv`
   - This will install the virtualenv python package for the system user
5. Run `venv venv` to create a virtual environment named "venv"

### For Windows Users

I have written a script to make the rest of the environment setup easy. If you run the script `scripts/update_py.ps1`, then the following will happen:

1. The virtual environment will be activated
2. All python dependencies will be installed in the virtual environment
3. A folder named /shared will be created
4. All python requirements will be stored in another requirements.txt file within the shared folder
5. All python dependencies will also be installed in the /shared folder

These steps are important because it will enable us to edit our lambda function and see those changes reflected in the API immediately. Without this /shared folder, we would have to rebuild our function every time a change is made. Builds with aws_lambda_powertools can be very time consuming, so this folder is a great tool for development.

### For Linux/Mac Users

Run the following commands to achieve the same result as the Windows Users. A description of why this step is important is above.

1. `./venv/Scripts/activate`
2. `pip install -r requirements.txt`
3. `mkdir shared`
4. `pip freeze > shared/requirements.txt`
5. `pip install -r shared/requirements.txt -t shared/python --upgrade`

## DynamoDB Local

DynamoDB local is an essential tool for developing with DynamoDB databases. The following steps ensure that you have DynamoDB Local installed correctly.

1. Verify docker is installed by running `docker --version`
2. Run `docker pull amazon/dynamodb-local`
3. Run `docker run -p 8000:8000 amazon/dynamodb-local` to start up the DynamoDB docker container locally.
   - You can also start the container manually in Docker Desktop by navigating to the DynamoDB Local container and clicking run
   - I prefer this way so that I don't need to waste space with an extra terminal

## Building and Starting the API

### For Windows Users

If you run `scripts/basa.ps1` from the command line, this should build and start the API for you. The API should run on "http://localhost:3000/"

### For Linux/Mac Users

Run the following commands to build and start your API:

1. `sam build`
2. `sam local start-api -t template.yaml --skip-pull-image`

# Endpoints

## Health

Endpoint: GET /health
HTTP Response Codes

- 200: The endpoint is healthy

Desired Response Structure

```
{
    "statusCode": 200,
    "body": {
      "message": "Healthy"
    }

}
```

## Get All Users

Endpoint: GET /users
HTTP Response Codes

- 200: If able to get users

Desired Response Structure

```
{
    "statusCode": 200,
    "body": {
      "users": <list of users>
    }
}
```

## Regiser a User

Endpoint: POST /register/:username

- username: the username of the user to register

Request Body

```
{
   "password": "<the-user-password>"
}
```

HTTP Response Codes

- 201 if user is successfully registered
- 400 if no password provided or weak password
- 409 if username already exists in DB
- 500 if there is a error accessing the table

Desired Response Structure

```
{
   "statusCode": 201,
   "body": {
      "username": "<username>",
      "table": "<table-user-was-added-into>",
      "message": "Successfully logged in user <username>",
      "jwt": "<a-new-jwt>"
   }
}
```

## Log In a User

Endpoint: POST /login/:username

- username: the username of the user to log in

Request Body

```
{
   "password" "<the-user-password>"
}
```

HTTP Reponse Codes

- 200 if user is successfully logs in with a JWT
- 400 if no password provided in request body
- 401 if the password provided is incorrect
- 409 if the user does not exist in the database
- 500 if there is an issue referencing the the database

Desired Response Structure

```
{
   "statusCode": 200,
   "body": {
      "username": "<username>",
      "table": "<table-user-was-added-into>",
      "message": "Successfully logged in user <username>",
      "jwt": "<a-new-jwt>",
   }
}
```

## Verify a JWT

Endpoint: PUT /verify

Request Body

```
{
   "jwt": "<the-jwt>"
}
```

HTTP Response Codes

- 200 if JWT is valid
- 400 if no jwt provided in the request body
- 401 if the token is invalid or expired

Desired Response Structure

```
{
   "statusCode": 200,
   "body": {
      "message": "Successfully validated jwt"
   }
}
```

# Testing

# Deployment
