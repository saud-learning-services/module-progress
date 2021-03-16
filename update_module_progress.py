"""
# -*- coding: utf-8 -*-
CREATED: Tue Aug 21 2018
MODIFIED: Sun Aug 02 2020

All Canvas LMS - REST API calls made using canvasapi python API wrapper:
https://github.com/ucfopen/canvasapi

@authors: Marko Prodanovic, Alison Myers, Jeremy Hidjaja

"""

import sys
from canvasapi.exceptions import Unauthorized
import pandas as pd
import src.interface as interface
import settings
from src.canvas_helpers import (
    get_modules,
    get_items,
    get_student_module_status,
    get_student_items_status,
    write_data_directory,
    clear_data_directory,
    write_tableau_directory,
    log_success,
    log_failure,
)

pd.set_option("display.max_columns", 500)


def main():
    """
    Main entry point for Module Progress Script
    """

    # Initialization
    usr_settings = interface.get_user_settings()
    course_ids = usr_settings["course_ids"]
    canvas = usr_settings["canvas"]
    tableau_dfs = []

    # clear any folders that are currently in there (leave tableau folder)
    clear_data_directory()

    # Getting course information for user-specified courses
    # Loops through courses and tries to get module/item information and create Pandas Dataframes
    # Writes dataframes to disk if successful
    # Prints error and skips course if unsuccessful
    for cid in course_ids:
        course = canvas.get_course(cid)
        # Calling helpers to get data from Canvas and build Pandas DataFrame's

        try:
            settings.status[str(cid)]["cname"] = course.name
            modules_df = get_modules(course)
            items_df = get_items(modules_df, course.name)
            student_module_status = get_student_module_status(course)
            student_items_status = get_student_items_status(
                course, student_module_status
            )
        except KeyError as error:
            log_failure(cid, error)
        except Unauthorized:
            log_failure(
                cid,
                "User not authorized to get module progress data for course: "
                + str(cid),
            )
        except IndexError:
            log_failure(cid, "Course must have students enrolled")
        except Exception as e:
            log_failure(cid, "Unexpected error: " + e)
        else:
            # Writing dataframes to disk
            dataframes = {
                "module_df": modules_df,
                "items_df": items_df,
                "student_module_df": student_module_status,
                "student_items_df": student_items_status,
            }
            tableau_dfs.append(student_items_status)
            write_data_directory(dataframes, cid)
            log_success(cid)

    try:
        write_tableau_directory(tableau_dfs)
    except Exception as e:
        print(e)
        print("Shutting down...")
        sys.exit()

    interface.render_status_table()
    print("\n\033[94m" + "***COMPLETED***" + "\033[91m")


if __name__ == "__main__":
    main()
