# Recorded by smithy_test. Review it for anything identifying before committing.
from inspect import cleandoc

from smithy_test import HTTPMockController


def install(controller: HTTPMockController) -> None:
    (
        controller.expect_operation("GetCallerIdentity")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "X-Amz-Sts-Extended-Request-Id": "RECORDED-REQUEST-ID",
                "Content-Type": "text/xml",
                "Content-Length": "469",
            },
            body=cleandoc(
                r"""
                <GetCallerIdentityResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
                  <GetCallerIdentityResult>
                    <Arn>arn:aws:sts::123456789012:assumed-role/Recor/recorded-sessionrecorded-sess</Arn>
                    <UserId>AROARECORDED000000001:recorded-sessionrecorded-sess</UserId>
                    <Account>123456789012</Account>
                  </GetCallerIdentityResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000001</RequestId>
                  </ResponseMetadata>
                </GetCallerIdentityResponse>
                """
            ),
        )
    )
