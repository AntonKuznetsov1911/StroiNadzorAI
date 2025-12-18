#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated Railway Environment Variables Updater

This script updates environment variables on Railway using their API.
You need to provide a Railway API token.
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load local .env
load_dotenv()

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.END} {msg}")

def print_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.END} {msg}")

def print_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.END} {msg}")

def print_warning(msg):
    print(f"{Colors.YELLOW}[WARNING]{Colors.END} {msg}")


def get_railway_token():
    """Get Railway API token from environment or prompt"""
    token = os.getenv("RAILWAY_API_TOKEN")

    if not token:
        print_warning("RAILWAY_API_TOKEN not found in environment")
        print_info("You can get your token from: https://railway.app/account/tokens")
        token = input("Enter your Railway API token: ").strip()

    return token


def update_railway_variables(token, project_id, service_id, variables):
    """Update environment variables on Railway using GraphQL API"""

    url = "https://backboard.railway.app/graphql/v2"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # GraphQL mutation to update variables
    for var_name, var_value in variables.items():
        mutation = """
        mutation variableUpsert($input: VariableUpsertInput!) {
          variableUpsert(input: $input)
        }
        """

        payload = {
            "query": mutation,
            "variables": {
                "input": {
                    "projectId": project_id,
                    "environmentId": service_id,
                    "name": var_name,
                    "value": var_value
                }
            }
        }

        print_info(f"Updating {var_name}...")

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            result = response.json()
            if "errors" in result:
                print_error(f"Failed to update {var_name}: {result['errors']}")
                return False
            else:
                print_success(f"Updated {var_name}")
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return False

    return True


def main():
    print("=" * 70)
    print("Railway Environment Variables Updater")
    print("=" * 70)
    print()

    # Get values from local .env
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not telegram_token or not openai_key:
        print_error("Missing environment variables in .env file!")
        sys.exit(1)

    print_info(f"TELEGRAM_BOT_TOKEN: {telegram_token[:20]}...{telegram_token[-10:]}")
    print_info(f"OPENAI_API_KEY: {openai_key[:20]}...{openai_key[-10:]}")
    print()

    # Get Railway token
    railway_token = get_railway_token()

    if not railway_token:
        print_error("No Railway token provided!")
        sys.exit(1)

    print()
    print_warning("You need to provide your Railway Project ID and Service ID")
    print_info("Find them in your Railway project URL:")
    print_info("https://railway.app/project/PROJECT_ID/service/SERVICE_ID")
    print()

    project_id = input("Enter Project ID: ").strip()
    service_id = input("Enter Service ID (Environment ID): ").strip()

    if not project_id or not service_id:
        print_error("Project ID and Service ID are required!")
        sys.exit(1)

    print()
    print_info("Updating variables on Railway...")
    print()

    variables = {
        "TELEGRAM_BOT_TOKEN": telegram_token,
        "OPENAI_API_KEY": openai_key
    }

    success = update_railway_variables(railway_token, project_id, service_id, variables)

    print()
    if success:
        print_success("All variables updated successfully!")
        print_info("Railway will automatically restart your service")
        print_info("Check logs at: https://railway.app/dashboard")
    else:
        print_error("Failed to update some variables")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_warning("Cancelled by user")
        sys.exit(0)
    except Exception as e:
        print()
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
