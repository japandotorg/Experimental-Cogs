from typing import Dict, List


def humanize_required_cogs(data: Dict[str, str]) -> List[str]:
    response: List[str] = []
    for key, value in data.items():
        url = value if isinstance(value, str) else None
        formatted = "[{}]({})".format(key, url) if url else key
        response.append(formatted)
    return response
