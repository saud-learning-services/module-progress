"""
Interface module for get_module_progress.py. Handles all actions
relating to user input, feedback from the console and token controls.

@authors: Marko Prodanovic, Alison Myers
"""
import os
import sys
from builtins import FileNotFoundError
import dotenv
import pandas as pd
from canvasapi import Canvas
from canvasapi.exceptions import InvalidAccessToken, ResourceDoesNotExist, Unauthorized
from pick import pick
from prettytable import PrettyTable
from pathlib import Path

import settings
from .canvas_helpers import log_failure

# CANVAS_INSTANCES = ['https://canvas.ubc.ca',
#                     'https://ubc.test.instructure.com',
#                     'https://ubcsandbox.instructure.com']

# This line fixes pylint no-member error for canvasapi data types:
# pylint:disable=E1101
# (not needed if not using pylint)


def get_user_settings():
    """Handles console printouts and collecting user input

    Returns:
        dictionary: key-value pairs defining settings
                    (canvas obj., instance base_url,
                    token, header and course id)

    Exceptions Caught:
        InvalidAccessToken: if value for token is not set in .env file or if token value is not valid
        RuntimeError: if there is no correctly formatted (w. necesary fields) .env file is in root directory
        ResourceDoesNotExist: if a course id from the course_id column in the course_entitlements.csv file cannot be found
        TypeError: if a value that isn't an integer appears under the course_id column is course_entitlements.csv
        Unauthorized: if a user does not have permission to access data for a specified course

    """
    print("\n")
    base_url = "https://canvas.ubc.ca"

    token = __load_token(base_url)

    canvas = Canvas(base_url, token)
    auth_header = {"Authorization": "Bearer " + token}
    course_ids = __load_ids()
    courses = []
    valid_cids = []
    for cid in course_ids:

        settings.status[str(cid)] = {
            "cname": None,
            "status": "Not executed",
            "message": "Has not been run yet",
        }
        try:
            course = canvas.get_course(cid)
        except InvalidAccessToken:
            __shut_down(
                "Invalid Access Token: Please check that the token provided is correct and still active"
            )
        except Unauthorized:
            log_failure(cid, "User not authorized to get course data")
        except TypeError:
            log_failure(cid, 'Invalid type on course id: "' + str(cid) + '"')
        except ResourceDoesNotExist:
            log_failure(cid, "Not Found Error: Please ensure correct course id")
        else:
            courses.append(course)
            valid_cids.append(cid)

    if not courses:
        __shut_down(
            "Error: course_entitlements.csv must contain at least one valid course code"
        )

    course_names = __make_selected_courses_string(courses)
    # if not admin:
    options = ["Yes, run for all courses", "Nevermind, end process"]
    title = "You have chosen to get Module Process: \n\n For: {} \n\n From: {}".format(
        course_names, base_url
    )
    continue_confirm = pick(options, title)

    if continue_confirm[1] == 0:
        print(
            "Getting Module Progress: \n For: {} \n From: {}".format(
                course_names, base_url
            )
        )
        print("------------------------------\n")
        print("Starting...")
        print("Getting module dataframe")

        return {
            "canvas": canvas,
            "base_url": base_url,
            "token": token,
            "header": auth_header,
            "course_ids": valid_cids,
        }

    print("Exiting user setup...")
    sys.exit()


def render_status_table():
    """Prints status items to terminal in tabular format

    PrettyTable Documentation: https://github.com/jazzband/prettytable
    """
    table = PrettyTable()
    R = "\033[0;31;40m"  # RED
    G = "\033[0;32;40m"  # GREEN
    N = "\033[0m"  # Reset

    table.field_names = ["Course Id", "Course Name", "Status", "Message"]
    for cid, info in settings.status.items():
        col = None
        if info["status"] == "Success":
            col = G
        else:
            col = R
        table.add_row([cid, info["cname"], col + info["status"] + N, info["message"]])

    print(table)


def __load_token(url):
    try:
        token = __read_token(url)
    except InvalidAccessToken:
        __shut_down(
            "Ivalid Access Token: No value set for token in .env file. Please provide a valid token"
        )
    except RuntimeError:
        print("Runtime Error: Could not load token!")
        print(
            "Ensure .env file is in root directory with token filled in for variable corresponding to given instance"
        )
        __shut_down(
            "Possible variable keys are: CANVAS_API_TOKEN, CANVAS_API_TOKEN_TEST, CANVAS_API_TOKEN_SANDBOX"
        )

    return token


def __load_ids():
    """Load course ids from .csv file

    Returns:
        listof course_id: All course ids in the course_ids column

    Exceptions Caught:
        FileNotFoundError: if there is no courses.csv file in src directory (SHUTS DOWN)
        KeyError: if there is no column titled "course id" in course_entitlements.csv (SHUTS DOWN)

    """

    cids = []

    try:
        entitlements_path = Path(f"{settings.ROOT_DIR}/course_entitlements.csv")
        dataframe = pd.read_csv(entitlements_path)
        for index, row in dataframe.iterrows():
            course_id = row["course_id"]

            if course_id not in cids:
                cids.append(course_id)
        return cids
    except FileNotFoundError:
        __shut_down(
            "File Not Found: There must be a file named course_entitlements.csv in ROOT directory."
        )
    except KeyError:
        __shut_down(
            'Key Error: Please ensure there is a column titled "course_id" present in course_entitlements.csv'
        )


def __make_selected_courses_string(courses):
    """Creates a string of comma separated string of course names.

    Used for user printout to indicate what courses the script is going to query

    Args:
        courses (listof Course): list of canvasapi course objects - specified by id in .csv file

    Returns:
        String: comma separated course names
    """
    indent = "    "
    selected = "\n" + indent + courses[0].name
    courses.pop(0)
    if courses:
        for course in courses:
            selected += ", " + "\n" + indent + course.name
    return selected


def __read_token(url):
    """Gets TOKEN from .env file in root directory

    Args:
        url (string): user selected BASE_URL (instance of Canvas being used)

    Raises:
        InvalidAccessToken: if token value is empty string and therefore not set
        RuntimeError: if there was a problem reading the .env file or the file did not have necessary varibles
                      for setting token values

    Returns
        String: the target TOKEN from the .env file
    """
    dotenv.load_dotenv(dotenv.find_dotenv(".env"))

    if url == "https://canvas.ubc.ca":
        token = os.environ.get("CANVAS_API_TOKEN")

    # if url == 'https://ubc.test.instructure.com':
    #     token = os.environ.get('CANVAS_API_TOKEN_TEST')

    # if url == 'https://ubcsandbox.instructure.com':
    #     token = os.environ.get('CANVAS_API_TOKEN_SANDBOX')

    if token == "":
        raise InvalidAccessToken("No token value.")

    if token is None:
        raise RuntimeError

    return token


def __shut_down(msg):
    """Shuts down the script

    Args:
        msg (string): message to print before printing 'Shutting down...' and exiting the script
    """
    print(msg)
    print("Shutting down...")
    sys.exit()
