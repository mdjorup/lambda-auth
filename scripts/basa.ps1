#!/bin/bash
sam build
sam local start-api -t template.yaml --skip-pull-image