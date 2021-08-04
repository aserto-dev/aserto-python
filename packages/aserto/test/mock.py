from asyncio import Future
from contextlib import contextmanager
from typing import Iterator
from unittest import mock

__all__ = ["mock_rest_request", "mock_grpc_request"]


@contextmanager
def mock_rest_request(response: object) -> Iterator[None]:
    mock_response = mock.MagicMock()
    mock_response.json.return_value = Future()
    mock_response.json.return_value.set_result(response)

    with mock.patch("aiohttp.ClientSession._request") as mock_client_session_request:
        mock_client_session_request.return_value = Future()
        mock_client_session_request.return_value.set_result(mock_response)

        yield

    mock_response.json.assert_called()
    mock_client_session_request.assert_called()


@contextmanager
def mock_grpc_request(response: object) -> Iterator[None]:
    mock_protocol = mock.MagicMock()
    mock_stream = mock_protocol.processor.connection.create_stream.return_value

    mock_release_stream = mock.MagicMock()
    mock_stream.send_request.return_value = Future()
    mock_stream.send_request.return_value.set_result(mock_release_stream)

    mock_stream.send_data.return_value = Future()
    mock_stream.send_data.return_value.set_result(None)

    with mock.patch("grpclib.client.Channel.__connect__") as mock_channel_connect, mock.patch(
        "grpclib.client.Stream.recv_message"
    ) as mock_stream_recv_message:
        mock_channel_connect.return_value = Future()
        mock_channel_connect.return_value.set_result(mock_protocol)

        mock_stream_recv_message.return_value = Future()
        mock_stream_recv_message.return_value.set_result(response)

        yield

    mock_channel_connect.assert_called()
    mock_stream.send_request.assert_called()
    mock_stream.send_data.assert_called()
    mock_stream_recv_message.assert_called()
