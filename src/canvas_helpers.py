"""
Helper functions for get_module_progress.py

***
All Canvas LMS REST API calls made using canvasapi python API wrapper:
https://github.com/ucfopen/canvasapi
***

@authors: Marko Prodanovic, Alison Myers, Jeremy Hidjaja 
"""
from ast import literal_eval
import datetime
import re
import os
import shutil
from tqdm import tqdm
import pandas as pd
import settings
from pathlib import Path


def create_dict_from_object(theobj, list_of_attributes):
    """given an object and list of attributes return a dictionary
    Args:
        theobj (a Canvas object)
        list_of_attributes (list of strings)
    Returns:
        mydict
    """

    def get_attribute_if_available(theobj, attrname):
        if hasattr(theobj, attrname):
            return {attrname: getattr(theobj, attrname)}
        else:
            return {attrname: None}

    mydict = {}
    for i in list_of_attributes:
        mydict.update(get_attribute_if_available(theobj, i))
    return mydict


def get_modules(course):
    """Returns all modules from specified course

    Makes a call to the CanvasAPI through Python API wrapper.
    Calls make_modules_dataframe() to convert response to properly formatted
    Pandas dataframe. Returns it.

    Args:
        course (canvasapi.course.Course): The course obj.
               from Canvas Python API wrapper

    Returns:
        DataFrame: Table with modules info for specified course

    Raises:
        KeyError: if request through canvasapi is unsuccessful or if dataframe creation and
                  handling results in errors
    """
    try:
        modules = course.get_modules(include=["items"], per_page=50)
        attrs = [
            "id",
            "name",
            "position",
            "unlock_at",
            "require_sequential_progress",
            "another item",
            "publish_final_grade",
            "prerequisite_module_ids",
            "published",
            "items_count",
            "items_url",
            "items",
            "course_id",
        ]

        modules_dict = [create_dict_from_object(m, attrs) for m in modules]
        modules_df = pd.DataFrame(modules_dict)
        modules_df = modules_df.rename(
            columns={
                "id": "module_id",
                "name": "module_name",
                "position": "module_position",
            }
        )

    except Exception:
        raise KeyError("Unable to get modules for course: " + course.name)
    else:
        return modules_df


def get_items(modules_df, cname):
    """Returns expanded modules data

    Given a modules dataframe, expand table data so that fields with a list get
    broken up into indiviaul rows per list item & dictionaries are broken up
    into separate columns.

    Args:
        module_df (DataFrame): modules DataFrame

    Returns:
        DataFrame: Table with all module info, a single row per item
                   and all item dict. attributes in a single column

    Raises:
        KeyError: if there is any issue expanding modules table or if module does not have items
    """
    try:
        expanded_items = _list_to_df(
            modules_df[["module_id", "module_name", "course_id", "items"]], "items"
        )

        items_df = _dict_to_cols(expanded_items, "items", "items_")

        items_df = _dict_to_cols(
            items_df.reset_index(drop=True),
            "items_completion_requirement",
            "items_completion_req_",
        )
    except KeyError:
        raise KeyError(
            f'Unable to expand module items for "{cname}." Please ensure all modules have items'
        )
    else:
        return items_df


def get_student_module_status(course):
    """Returns DataFrame with students' module progress

    Given a course object, gets students registered in that course (API Request)
    For each student, gets module info pertaining to that student (API Request)
    Returns info in Pandas DataFrame table format.

    Args:
        course (canvasapi.course.Course): The course obj.
               from Canvas Python API wrapper

    Returns:
        DataFrame: Table containing module progress data for each student.
                   Each student has a single entry per module in specified
                   course. EX.
                   row 0: student0, module0
                   row 1: student0, module1
                   row 2: student1, module0
                   row 3: student1, module1
    """

    students_df = _get_students(course)

    print("Getting student module info for " + course.name)
    student_module_status = pd.DataFrame()

    num_rows = len(list(students_df.iterrows()))
    with tqdm(total=num_rows) as pbar:
        for i, row in students_df.iterrows():
            pbar.update(1)
            sid = row["id"]
            student_data = course.get_modules(
                student_id=sid, include=["items"], per_page=50
            )
            attrs = [
                "id",
                "name",
                "position",
                "unlock_at",
                "require_sequential_progress",
                "publish_final_grade",
                "prerequisite_module_ids",
                "state",
                "completed_at",
                "items_count",
                "items_url",
                "items",
                "course_id",
            ]

            # make student data into dictionary
            student_rows_dict = [
                create_dict_from_object(m, attrs) for m in student_data
            ]

            # make dictionary into df
            student_rows = pd.DataFrame(student_rows_dict)

            student_rows["student_id"] = str(sid)
            student_rows["student_name"] = row["name"]
            student_rows["sortable_student_name"] = row["sortable_name"]
            student_module_status = student_module_status.append(
                student_rows, ignore_index=True, sort=False
            )
            # note, kept getting sort error future warning
            # might want to check this in future that Sort should be false

    student_module_status = student_module_status.rename(
        columns={
            "id": "module_id",
            "name": "module_name",
            "position": "module_position",
        }
    )
    return student_module_status


def get_student_items_status(course, module_status):
    """Returns expanded student module status data table

    Args:
        course (canvasapi.course.Course): The course obj.
               from Canvas Python API wrapper.
        module_status (DataFrame): student module status DataFrame

    Returns:
        DataFrame: Expanded table with same information as module_status DF.
                   Items list exapanded -> single row per item
                   Items dict. expanded -> single col per attribute
    """
    expanded_items = _list_to_df(module_status, "items")
    expanded_items = _dict_to_cols(expanded_items, "items", "items_")
    student_items_status = _dict_to_cols(
        expanded_items, "items_completion_requirement", "item_cp_req_"
    ).reset_index(drop=True)
    student_items_status["course_id"] = course.id
    student_items_status["course_name"] = course.name

    # pull out completed_at column as list
    items_status_list = student_items_status["completed_at"].values.tolist()
    # clean/format the datetime string (to be more interpretable in Tableau)
    cleaned = map(__clean_datetime_value, items_status_list)
    # put cleaned values back into dataframe
    student_items_status["completed_at"] = list(cleaned)
    student_items_status = student_items_status[
        [
            "completed_at",
            "course_id",
            "module_id",
            "items_count",
            "module_name",
            "module_position",
            "state",
            "unlock_at",
            "student_id",
            "student_name",
            "items_id",
            "items_title",
            "items_position",
            "items_indent",
            "items_type",
            "items_module_id",
            "item_cp_req_type",
            "item_cp_req_completed",
            "course_name",
        ]
    ]
    return student_items_status


def __clean_datetime_value(datetime_string):
    """Given"""
    if datetime_string is None:
        return datetime_string

    if isinstance(datetime_string, str):
        x = datetime_string.replace("T", " ")
        return x.replace("Z", "")

    raise TypeError("Expected datetime_string to be of type string (or None)")


def write_data_directory(dataframes, cid):
    """Writes dataframes to directory titled by value of cid and items dataframe to
       tableau directory

    Iterates through dataframes dictionary and writes each one to disk (<key>.csv)
    Makes *Course output* directory in data folder named <cid> (or writes to existing
    if one already exists with that name)
    Makes *Tableau* output directory called "Tableau" where all student_items dataframes will
    be put for ease of import and union in tableau

    Args:
        dataframes (dictionary): dictionary of DataFrames
                   Format -> { name, DataFrame,... }
        dir_name (string): directory name
    """

    course_path = _make_output_dir(cid)
    for name, dataframe in dataframes.items():
        path = Path(f"{course_path}/{name}.csv")
        dataframe.to_csv(path, index=False)


def clear_data_directory():
    """
    Clears entire data directory except for Tableau folder
    Directory path : module_progress/data
    """

    root = os.path.dirname(os.path.abspath(__file__))[:-4]
    data_path = Path(f"{root}/data")

    for subdir in os.listdir(data_path):
        path = data_path / subdir
        if subdir != "Tableau" and subdir != ".gitkeep" and subdir != ".DS_Store":
            shutil.rmtree(path, ignore_errors=False, onerror=None)


def write_tableau_directory(list_of_dfs):
    """Creates a directory titled Tableau containing 3 items:
            course_entitlements.csv --> permissions table for Tableau server
            module_data.csv         --> unioned data for Tableau
            status.csv              --> details the success of the most recent run

    Also creates a .zip with the contents of the Tableau folder in the 'archive' directory
    """
    tableau_path = _make_output_dir("Tableau")
    union = pd.concat(list_of_dfs, axis=0, ignore_index=True)
    module_data_output_path = tableau_path / "module_data.csv"
    union.to_csv(module_data_output_path, index=False)

    root = os.path.dirname(os.path.abspath(__file__))[:-4]

    # Copy the course_entitlements.csv into the Tableau folder
    src = Path(f"{root}/course_entitlements.csv")
    dst = Path(f"{root}/data/Tableau/course_entitlements.csv")
    shutil.copyfile(src, dst)

    current_dt = datetime.datetime.now()
    dir_name = str(current_dt.strftime("%Y-%m-%d %H.%M.%S"))
    src = tableau_path
    dst = Path(f"{root}/archive/{dir_name}")
    shutil.make_archive(dst, "zip", src)
    _output_status_table(tableau_path)


def _output_status_table(tableau_path):
    """
    Creates .csv file for log folder that specifies run status for each course.
    Log is titled by date time and table status info reflects most recent run.
    """

    current_dt = datetime.datetime.now()
    cols = ["Course Id", "Course Name", "Status", "Message", "Data Updated On"]
    data = []
    for cid, info in settings.status.items():
        row = [cid, info["cname"], info["status"], info["message"], current_dt]
        data.append(row)

    dataframe = pd.DataFrame(data, columns=cols)

    file_name = str(current_dt.strftime("%Y-%m-%d %H.%M.%S")) + ".csv"

    status_log_path = Path(f"{settings.ROOT_DIR}/status_log/{file_name}")
    dataframe.to_csv(status_log_path, index=False)

    status_path = tableau_path / "status.csv"
    dataframe.to_csv(status_path, index=False)


def log_failure(cid, msg):
    """Adds failure log to global status object

    Args:
        cid (Integer): course id who's status has changed - used to create log entry
        msg (String): description of the failure
    """
    settings.status[str(cid)]["status"] = "Failed"
    settings.status[str(cid)]["message"] = msg


def log_success(cid):
    """Adds success log to glbal status object

    Args:
        cid (Integer): course id who's status has changed - used to create log entry
    """
    settings.status[str(cid)]["status"] = "Success"
    settings.status[str(cid)][
        "message"
    ] = "Course folder has been created in data directory"


def _get_students(course):
    """Returns DataFrame table with students enrolled in specified course

    Makes a request to Canvas LMS REST API through Canvas Python API Wrapper
    Calls make_dataframe to convert response to Pandas DataFrame. Returns
    DataFrame.

    Args:
        course (canvasapi.course.Course): The course obj.
               from Canvas Python API wrapper

    Returns:
        DataFrame: Students table

    """
    # print("Getting student list")
    students = course.get_users(
        include=["test_student", "email"], enrollment_type=["student"], per_page=50
    )
    attrs = [
        "id",
        "name",
        "created_at",
        "sortable_name",
        "short_name",
        "sis_user_id",
        "integration_id",
        "login_id",
        "pronouns",
    ]

    students_data = [create_dict_from_object(s, attrs) for s in students]
    students_df = pd.DataFrame(students_data)
    return students_df


def _make_output_dir(name):
    """Check if output directory exists in data folder, it not makes one

    Args:
        name (string): The directory name

    Returns:
        String: path to the newly created directory
    """
    root = os.path.dirname(os.path.abspath(__file__))[:-4]
    directory_path = Path(f"{root}/data/{name}")
    # print(directory_path)
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
    return directory_path


# def _make_dataframe(paginated_list):
#     """Convert data of type PaginatedList to a Pandas DataFrame

#     Args:
#         paginated_list (PaginatedList): PaginatedList object
#                        (res from canvasapi wrapper)
#     Returns:
#         DataFrame: Pandas DataFrame table containing info from paginated_list
#                    Constructed from objects attributes - The JSON object used
#                    to build the PaginatedList element
#     """
#     json_list = []
#     for element in paginated_list:
#         json_list.append(element.attributes)
#     dataframe = pd.DataFrame(json_list)
#     return dataframe


def _dict_to_cols(dataframe, col_to_expand, expand_name):
    """Expands column that contains dict to multiple columns (1/dict key)

    Transforms column specified to appropriate dict (all items are strings)
    Returns DataFrame with original index

    Args:
        dataframe (DataFrame): a Panadas DataFrame that needs expanding
        col_to_expand (string): the name of the column to expand
        expanded_name (string): the prefix for the newly expanded columns
        EX. (w. expanded_name = 'items_').
            items (dict in single col.):
                {'id': 85224, 'title': 'Page 1', 'position': 1, ...}
            EXPANDS TO
                => items_id: 8424,
                   items_title: Page 1,
                   items_position: 1
                   ...
    Returns:
        DataFrame: New dataframe with specified columns expanded

    """
    dataframe[col_to_expand] = dataframe[col_to_expand].apply(_all_dict_to_str)
    original_df = dataframe.drop([col_to_expand], axis=1)
    extended_df = dataframe[col_to_expand].apply(pd.Series)
    extended_df.columns = [
        i
        if bool(re.search(expand_name, i))
        else "{}{}".format(str(expand_name), str(i))
        for i in extended_df.columns
    ]
    new_df = pd.concat([original_df, extended_df], axis=1, ignore_index=False)
    return new_df


def _list_to_df(dataframe, col_to_expand):
    """Expands column that contains list to multiple rows (1/list item)

    col_to_expand specifies a column that contains list entries
    Expands column list into multiple rows -- one per list item
    Keeps original columns.

    Args:
        dataframe (DataFrame): a Panadas DataFrame that needs expanding
        col_to_expand: the column that contains list entries
    Returns:
        DataFrame: with original index
    """
    series = (
        dataframe.apply(lambda x: pd.Series(x[col_to_expand]), axis=1)
        .stack()
        .reset_index(level=1, drop=True)
    )
    series.name = col_to_expand
    new_df = dataframe.drop(col_to_expand, axis=1).join(series)
    return new_df


def _all_dict_to_str(d):
    """Makes all dictionary values into strings

    Handles dictionaries returned from canvas.
    When data returned some items are not strings - changes all items to strings.
    Some data becomes string in DataFrames i.e. "{'a': 'string'}", transforms to dict.
    Returns Dict where all values are strings.

    Args:
        d (dictionary): dictionary with <key, value> pairs
    Returns:
        Dictionary: all values are strings
    """
    # if its a dict, change items to strings
    if isinstance(d, dict):
        new = {k: str(v) for k, v in d.items()}
        return new
    else:
        if pd.isnull(d):
            pass
        else:
            d = literal_eval(d)
            new = {k: str(v) for k, v in d.items()}
            return new
