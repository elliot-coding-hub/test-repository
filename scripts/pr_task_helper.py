import argparse
import json as _json
import re
import typing
import urllib.error
import urllib.parse
import urllib.request
from email.message import Message
from enum import Enum

TASK_ID_PROPERTY = "Task ID"
TASK_STATUS_PROPERTY = "Status"

parser = argparse.ArgumentParser()
parser.add_argument("-secret", help="Please set notion api secret key")
parser.add_argument("-database_id", help="Please set notion database-id")
parser.add_argument("-pr_title", help="Please set pr-title")
args = parser.parse_args()


class Response(typing.NamedTuple):
    body: str
    headers: Message
    status: int
    error_count: int = 0

    def json(self) -> any:
        """
        Decode body's JSON.

        Returns:
            Pythonic representation of the JSON object
        """
        try:
            output = _json.loads(self.body)
        except _json.JSONDecodeError:
            output = ""
        return output


def request(
        url: str,
        data: dict = None,
        params: dict = None,
        headers: dict = None,
        method: str = "GET",
        data_as_json: bool = True,
        error_count: int = 0,
) -> Response:
    if not url.casefold().startswith("http"):
        raise urllib.error.URLError("Incorrect and possibly insecure protocol in url")
    method = method.upper()
    request_data = None
    headers = headers or {}
    data = data or {}
    params = params or {}
    headers = {"Accept": "application/json", **headers}

    if method == "GET":
        params = {**params, **data}
        data = None

    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True, safe="/")

    if data:
        if data_as_json:
            request_data = _json.dumps(data).encode()
            headers["Content-Type"] = "application/json; charset=UTF-8"
        else:
            request_data = urllib.parse.urlencode(data).encode()

    httprequest = urllib.request.Request(
        url, data=request_data, headers=headers, method=method
    )

    try:
        with urllib.request.urlopen(httprequest) as httpresponse:
            response = Response(
                headers=httpresponse.headers,
                status=httpresponse.status,
                body=httpresponse.read().decode(
                    httpresponse.headers.get_content_charset("utf-8")
                ),
            )
    except urllib.error.HTTPError as e:
        response = Response(
            body=str(e.reason),
            headers=e.headers,
            status=e.code,
            error_count=error_count + 1,
        )

    return response


class Request:
    def post(self, url: str, headers: dict[str, any], json: dict[str, any]) -> Response:
        return request(method="POST", url=url, headers=headers, data=json)

    def patch(self, url: str, headers: dict[str, any], json: dict[str, any]) -> Response:
        return request(method="PATCH", url=url, headers=headers, data=json)


requests = Request()


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
