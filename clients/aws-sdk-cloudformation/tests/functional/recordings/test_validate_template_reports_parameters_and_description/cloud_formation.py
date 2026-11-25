# Recorded by smithy_test. Review it for anything identifying before committing.
from inspect import cleandoc

from smithy_test import HTTPMockController


def install(controller: HTTPMockController) -> None:
    (
        controller.expect_operation("ValidateTemplate")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "515",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <ValidateTemplateResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <ValidateTemplateResult>
                    <Description>aws-sdk-python recorded test</Description>
                    <Parameters>
                      <member>
                        <NoEcho>false</NoEcho>
                        <DefaultValue>0</DefaultValue>
                        <ParameterKey>Delay</ParameterKey>
                      </member>
                    </Parameters>
                  </ValidateTemplateResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000001</RequestId>
                  </ResponseMetadata>
                </ValidateTemplateResponse>
                """
            ),
        )
    )
