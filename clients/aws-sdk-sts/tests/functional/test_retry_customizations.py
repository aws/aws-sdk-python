# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any

import pytest
from aws_sdk_sts.client import STSClient
from aws_sdk_sts.config import STSConfig
from aws_sdk_sts.models import GetCallerIdentityInput
from smithy_core.client import RequestPipeline
from smithy_test import mock


# TODO: retry IDPCommunicationError
@pytest.mark.skip
def test_idp_communication_error_is_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    # Only the attempt count matters here, so the backoff waits are skipped.
    """STS retries IDPCommunicationError."""
    monkeypatch.setattr(RequestPipeline, "_sleep", _no_sleep)
    client = STSClient(STSConfig.resolve(region="us-west-2"))
    controller = mock(client)
    controller.expect_request(hostname="/./").respond_with(
        status_code=400,
        headers={"content-type": "text/xml"},
        body="""<ErrorResponse>
    <Error>
        <Type>Sender</Type>
        <Code>IDPCommunicationError</Code>
        <Message>Oh No 1</Message>
    </Error>
    <RequestId>c6104cbe-af31-11e0-8154-cbc7ccf896c7</RequestId>
</ErrorResponse>""",
    ).respond_with(
        status_code=400,
        headers={"content-type": "text/xml"},
        body="""<ErrorResponse>
    <Error>
        <Type>Sender</Type>
        <Code>IDPCommunicationError</Code>
        <Message>Oh No 2</Message>
    </Error>
    <RequestId>c6104cbe-af31-11e0-8154-cbc7ccf896c7</RequestId>
</ErrorResponse>""",
    ).respond_with(
        status_code=200,
        headers={"content-type": "text/xml"},
        body="""<GetCallerIdentityResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
  <GetCallerIdentityResult>
    <Arn>arn:aws:sts::123456789012:assumed-role/demo/TestAR</Arn>
    <UserId>ARO123EXAMPLE123:TestAR</UserId>
    <Account>123456789012</Account>
  </GetCallerIdentityResult>
  <ResponseMetadata>
    <RequestId>c6104cbe-af31-11e0-8154-cbc7ccf896c7</RequestId>
  </ResponseMetadata>
</GetCallerIdentityResponse>""",
    )

    client.get_caller_identity(GetCallerIdentityInput())

    assert len(controller.requests) == 3


def _no_sleep(self: RequestPipeline[Any, Any], delay: float) -> None:
    pass
