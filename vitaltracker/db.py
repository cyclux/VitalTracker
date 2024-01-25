import os
from datetime import date
from pathlib import Path
import sqlalchemy as sql
from sqlalchemy.exc import SQLAlchemyError
from typing import List
import streamlit as st
from dotenv import load_dotenv


def check_success(result: sql.CursorResult) -> str:
    """Checks if a SQL statement was successful.

    Args:
        result (sql.CursorResult): Result of executing the SQL statement.

    Returns:
        str: A message indicating whether the SQL statement was successful.

    Raises:
        SQLAlchemyError: If there was an error executing the SQL statement.
    """
    if result.rowcount == 1:
        return ":green[Gespeichert]"
    else:
        return ":red[Fehler bei der Speicherung. Versuche es erneut.]"


def get_postgres_pw() -> str:
    """Gets the PostgreSQL database password from the .env file.

    Returns:
        str: The PostgreSQL database password read from the
            PG_PASSWORD environment variable.

    Raises:
        SystemExit: If the PG_PASSWORD environment variable is not set,
            the program will stop execution and print an error message.

    Note:
        Relies on the python-dotenv package to load environment variables
        from the .env file.
    """
    load_dotenv(Path(".env"))
    pg_pw = os.environ.get("PG_PASSWORD")

    if pg_pw is None:
        st.write("Kein DB Passwort gefunden. Bitte ein Passwort in der .env anlegen.")
        st.stop()

    return pg_pw


def get_postgres_uri() -> dict:
    """Get PostgreSQL database URI.

    Constructs the PostgreSQL database URI from environment variables.

    Returns:
        dict: Dictionary containing the PostgreSQL database URI
            under the "uri" key.
    """
    return {
        "uri": f"postgresql://postgres:{get_postgres_pw()}@docker_db:5432/moodfit_db",
    }


def get_sql_engine(db_config: dict) -> sql.Engine:
    """Get SQLAlchemy engine instance

    Creates and initializes a SQLAlchemy engine based on the provided
    database configuration.

    Args:
        db_config (dict): Database configuration dictionary containing the
                        database URI and credentials

    Returns:
        sql.Engine: SQLAlchemy engine instance for the database
    """
    engine = sql.create_engine(db_config["uri"])
    engine.connect()
    return engine


def add_diary_record(items: dict, sql_engine: sql.Engine) -> str:
    """Adds a record to the diary table in the moodfit_db database.

    Args:
        items (dict): A dictionary containing the diary record data.
        sql_engine (sqlalchemy.engine.Engine): SQLAlchemy engine instance for the database.

    Returns:
        str: A message indicating whether the insert was successful.

    Raises:
        SQLAlchemyError: If there was an error executing the SQL statement.

    Note:
        Uses an UPSERT statement to insert/update the record.
    """
    upsert_stmt = sql.text(
        """
        INSERT INTO diary (date, tasks, sleep, bodybattery_min, bodybattery_max, steps, body, psyche, dizzy, comment)
        VALUES (:date, :tasks, :sleep, :bodybattery_min, :bodybattery_max, :steps, :body, :psyche, :dizzy, :comment)
        ON CONFLICT (date) DO UPDATE SET
            tasks = EXCLUDED.tasks,
            sleep = EXCLUDED.sleep,
            bodybattery_min = EXCLUDED.bodybattery_min,
            bodybattery_max = EXCLUDED.bodybattery_max,
            steps = EXCLUDED.steps,
            body = EXCLUDED.body,
            psyche = EXCLUDED.psyche,
            dizzy = EXCLUDED.dizzy,
            comment = EXCLUDED.comment
    """
    )
    # Execute the SQL statement with the provided items
    try:
        with sql_engine.connect() as conn:
            result = conn.execute(upsert_stmt, items)
            conn.commit()
            response_txt = check_success(result)

    except SQLAlchemyError as e:
        response_txt = f":red[Datenbankfehler:] {e}"

    return response_txt


def get_diary_record_by_date(date: date, sql_engine: sql.Engine) -> dict:
    """Query the diary table for a specific date and return the record as a dict.

    Args:
        date (str): The date to query in the diary table.
        sql_engine (sql.Engine): SQLAlchemy engine instance for the database.

    Returns:
        dict: The diary record of the specified date, or None if no record is found.
    """
    # Define the SQL SELECT statement
    columns: List[sql.ColumnElement] = [
        sql.column("date"),
        sql.column("tasks"),
        sql.column("sleep"),
        sql.column("bodybattery_min"),
        sql.column("bodybattery_max"),
        sql.column("steps"),
        sql.column("body"),
        sql.column("psyche"),
        sql.column("dizzy"),
        sql.column("comment"),
    ]
    select_stmt = (
        sql.select(*columns)
        .select_from(sql.table("diary"))
        .where(sql.column("date") == date)
    )

    # Execute the query and fetch the result
    with sql_engine.connect() as conn:
        result = conn.execute(select_stmt).fetchone()

    # If a record is found, return as a dictionary
    if result:
        return {
            "date": result[0],
            "tasks": result[1],
            "sleep": result[2],
            "bodybattery_min": result[3],
            "bodybattery_max": result[4],
            "steps": result[5],
            "body": result[6],
            "psyche": result[7],
            "dizzy": result[8],
            "comment": result[9],
        }
    else:
        return {}