import pytest
from pytest_httpx import HTTPXMock
from whatsapp.client import WhatsAppClient
from gowa_sdk import ApiResponse


@pytest.fixture
def client():
    return WhatsAppClient(base_url="http://test-api")


@pytest.mark.asyncio
async def test_login(client: WhatsAppClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://test-api/app/login",
        json={
            "code": "200",
            "message": "Success",
            "results": {"qr_link": "test_qr", "qr_duration": 60},
        },
    )
    response = await client.login()
    assert isinstance(response, ApiResponse)
    assert response.code == "200"
    assert response.results is not None
    assert response.results.qr_link == "test_qr"


@pytest.mark.asyncio
async def test_get_user_info(client: WhatsAppClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://test-api/user/info?phone=1234567890",
        json={
            "code": "200",
            "message": "Success",
            "results": {
                "verified_name": "Test User",
                "status": "Hey there!",
                "picture_id": "http://pfp.url",
                "devices": [],
            },
        },
    )
    response = await client.get_user_info("1234567890")
    assert isinstance(response, ApiResponse)
    assert response.code == "200"
    assert response.results is not None
    assert response.results.verified_name == "Test User"


@pytest.mark.asyncio
async def test_get_my_jid(client: WhatsAppClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://test-api/devices",
        json={
            "code": "SUCCESS",
            "message": "List devices",
            "results": [
                {
                    "id": "af3503e1-3132-4b3a-9eb1-e107f2adf71d",
                    "display_name": "Mini-me",
                    "state": "logged_in",
                    "jid": "19403633312@s.whatsapp.net",
                    "created_at": "2026-07-25T13:58:12.122885835Z",
                }
            ],
        },
    )
    my_jid = await client.get_my_jid()
    assert my_jid.user == "19403633312"
    assert my_jid.server == "s.whatsapp.net"


@pytest.mark.asyncio
async def test_send_message(client: WhatsAppClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://test-api/send/message",
        method="POST",
        json={
            "code": "200",
            "message": "Success",
            "results": {"message_id": "msg_123", "status": "SENT"},
        },
    )
    from gowa_sdk import SendMessageRequest

    request = SendMessageRequest(phone="1234567890", message="Hello")
    response = await client.send_message(request)
    assert isinstance(response, ApiResponse)
    assert response.code == "200"
    assert response.results is not None
    assert response.results.message_id == "msg_123"
