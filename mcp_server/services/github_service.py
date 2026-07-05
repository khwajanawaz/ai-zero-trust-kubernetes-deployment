import base64
import requests


def fetch_github_file_content(
    repo_owner: str,
    repo_name: str,
    branch: str,
    file_path: str,
    github_token: str | None = None,
) -> str:
    """
    Fetch a file from GitHub repository and return its decoded text content.
    Works for public repos and private repos (if token is provided).
    """

    url = (
        f"https://api.github.com/repos/"
        f"{repo_owner}/{repo_name}/contents/{file_path}?ref={branch}"
    )

    headers = {
        "Accept": "application/vnd.github+json",
    }

    # Add token for private repositories
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code == 404:
        raise ValueError("GitHub repository or file not found")
    if response.status_code == 401:
        raise ValueError("Unauthorized: invalid or missing GitHub token")
    if response.status_code == 403:
        raise ValueError("Forbidden: token does not have access to this repository")

    response.raise_for_status()

    data = response.json()

    if data.get("encoding") != "base64":
        raise ValueError("Unexpected GitHub file encoding")

    encoded_content = data.get("content", "")
    if not encoded_content:
        raise ValueError("GitHub file content is empty")

    decoded_content = base64.b64decode(encoded_content).decode("utf-8")
    return decoded_content