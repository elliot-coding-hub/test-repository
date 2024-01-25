import argparse
import re
from enum import Enum

import requests

TASK_ID_PROPERTY = "Task ID"
TASK_STATUS_PROPERTY = "Status"

parser = argparse.ArgumentParser()
parser.add_argument("-secret", help="Please set notion api secret key")
parser.add_argument("-database_id", help="Please set notion database-id")
parser.add_argument("-pr_title", help="Please set pr-title")
args = parser.parse_args()


class Status(str, Enum):
    NOT_STARTED: str = "Not started"
    IN_PROGRESS: str = "In progress"
    DONE: str = "Done"
    ARCHIVED: str = "Archived"


def get_task_pk_from_title(title: str) -> int:
    match = re.search(r'\[TSK-(\d+)\]', title)
    task_pk = int(match.group(1))
    return task_pk


def get_tasks(secret: str, database_id: str, task_pk: int) -> list[dict[str, any]]:
    response = requests.post(
        url=f"https://api.notion.com/v1/databases/{database_id}/query",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {secret}",
            "Notion-Version": "2022-06-28"
        },
        json={
            "filter": {
                "property": TASK_ID_PROPERTY,
                "unique_id": {
                    "equals": task_pk
                }
            }
        }
    )

    result = response.json()["results"]
    return result


def finish_task(secret: str, task_id: str) -> None:
    response = requests.patch(
        url=f"https://api.notion.com/v1/pages/{task_id}",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {secret}",
            "Notion-Version": "2022-06-28"
        },
        json={
            "properties": {
                TASK_STATUS_PROPERTY: {
                    "status": {
                        "name": Status.DONE
                    }
                }
            }
        }
    )

    result = response.json()
    return result


if __name__ == '__main__':
    secret = args.secret
    database_id = args.database_id
    pr_title = args.pr_title

    task_pk = get_task_pk_from_title(title=pr_title)

    tasks = get_tasks(secret=secret, database_id=database_id, task_pk=task_pk)
    for task in tasks:
        finish_task(secret=secret, task_id=task["id"])
