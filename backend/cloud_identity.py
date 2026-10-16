"""Identity tokens for private Cloud Run service-to-service calls."""

import asyncio


def _token(audience):
    import google.auth.transport.requests
    import google.oauth2.id_token
    request = google.auth.transport.requests.Request()
    return google.oauth2.id_token.fetch_id_token(request, audience)


async def headers(audience):
    return {"Authorization": f"Bearer {await asyncio.to_thread(_token, audience)}"} if audience else {}
