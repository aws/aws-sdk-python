# Recorded by smithy_test. Review it for anything identifying before committing.
from inspect import cleandoc

from smithy_test import HTTPMockController


def install(controller: HTTPMockController) -> None:
    (
        controller.expect_operation("CreateStack")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "478",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <CreateStackResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <CreateStackResult>
                    <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                    <OperationId>00000000-0000-4000-8000-000000000002</OperationId>
                  </CreateStackResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000003</RequestId>
                  </ResponseMetadata>
                </CreateStackResponse>
                """
            ),
        )
    )
    (
        controller.expect_operation("DescribeStacks")
        .times(14)
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "1408",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:36:01.162Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000002</OperationId>
                            <OperationType>CREATE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackStatusReason>User Initiated</StackStatusReason>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>CREATE_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags/>
                      </member>
                    </Stacks>
                  </DescribeStacksResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000004</RequestId>
                  </ResponseMetadata>
                </DescribeStacksResponse>
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "1577",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:36:01.162Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <DeletionTime>2026-11-24T20:36:04.955Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000005</OperationId>
                            <OperationType>ROLLBACK</OperationType>
                          </member>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000002</OperationId>
                            <OperationType>CREATE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>ROLLBACK_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags/>
                      </member>
                    </Stacks>
                  </DescribeStacksResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000006</RequestId>
                  </ResponseMetadata>
                </DescribeStacksResponse>
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "1577",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:36:01.162Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <DeletionTime>2026-11-24T20:36:04.955Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000005</OperationId>
                            <OperationType>ROLLBACK</OperationType>
                          </member>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000002</OperationId>
                            <OperationType>CREATE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>ROLLBACK_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags/>
                      </member>
                    </Stacks>
                  </DescribeStacksResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000007</RequestId>
                  </ResponseMetadata>
                </DescribeStacksResponse>
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "1577",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:36:01.162Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <DeletionTime>2026-11-24T20:36:04.955Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000005</OperationId>
                            <OperationType>ROLLBACK</OperationType>
                          </member>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000002</OperationId>
                            <OperationType>CREATE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>ROLLBACK_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags/>
                      </member>
                    </Stacks>
                  </DescribeStacksResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000008</RequestId>
                  </ResponseMetadata>
                </DescribeStacksResponse>
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "1577",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:36:01.162Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <DeletionTime>2026-11-24T20:36:04.955Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000005</OperationId>
                            <OperationType>ROLLBACK</OperationType>
                          </member>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000002</OperationId>
                            <OperationType>CREATE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>ROLLBACK_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags/>
                      </member>
                    </Stacks>
                  </DescribeStacksResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000009</RequestId>
                  </ResponseMetadata>
                </DescribeStacksResponse>
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "1577",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:36:01.162Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <DeletionTime>2026-11-24T20:36:04.955Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000005</OperationId>
                            <OperationType>ROLLBACK</OperationType>
                          </member>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000002</OperationId>
                            <OperationType>CREATE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>ROLLBACK_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags/>
                      </member>
                    </Stacks>
                  </DescribeStacksResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000010</RequestId>
                  </ResponseMetadata>
                </DescribeStacksResponse>
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "1577",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:36:01.162Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <DeletionTime>2026-11-24T20:36:04.955Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000005</OperationId>
                            <OperationType>ROLLBACK</OperationType>
                          </member>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000002</OperationId>
                            <OperationType>CREATE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>ROLLBACK_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags/>
                      </member>
                    </Stacks>
                  </DescribeStacksResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000011</RequestId>
                  </ResponseMetadata>
                </DescribeStacksResponse>
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "1577",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:36:01.162Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <DeletionTime>2026-11-24T20:36:04.955Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000005</OperationId>
                            <OperationType>ROLLBACK</OperationType>
                          </member>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000002</OperationId>
                            <OperationType>CREATE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>ROLLBACK_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags/>
                      </member>
                    </Stacks>
                  </DescribeStacksResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000012</RequestId>
                  </ResponseMetadata>
                </DescribeStacksResponse>
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "1577",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:36:01.162Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <DeletionTime>2026-11-24T20:36:04.955Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000005</OperationId>
                            <OperationType>ROLLBACK</OperationType>
                          </member>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000002</OperationId>
                            <OperationType>CREATE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>ROLLBACK_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags/>
                      </member>
                    </Stacks>
                  </DescribeStacksResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000013</RequestId>
                  </ResponseMetadata>
                </DescribeStacksResponse>
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "1577",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:36:01.162Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <DeletionTime>2026-11-24T20:36:04.955Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000005</OperationId>
                            <OperationType>ROLLBACK</OperationType>
                          </member>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000002</OperationId>
                            <OperationType>CREATE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>ROLLBACK_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags/>
                      </member>
                    </Stacks>
                  </DescribeStacksResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000014</RequestId>
                  </ResponseMetadata>
                </DescribeStacksResponse>
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "1577",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:36:01.162Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <DeletionTime>2026-11-24T20:36:04.955Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000005</OperationId>
                            <OperationType>ROLLBACK</OperationType>
                          </member>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000002</OperationId>
                            <OperationType>CREATE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>ROLLBACK_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags/>
                      </member>
                    </Stacks>
                  </DescribeStacksResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000015</RequestId>
                  </ResponseMetadata>
                </DescribeStacksResponse>
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "1574",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:36:01.162Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <DeletionTime>2026-11-24T20:36:04.955Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000005</OperationId>
                            <OperationType>ROLLBACK</OperationType>
                          </member>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000002</OperationId>
                            <OperationType>CREATE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>ROLLBACK_COMPLETE</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags/>
                      </member>
                    </Stacks>
                  </DescribeStacksResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000016</RequestId>
                  </ResponseMetadata>
                </DescribeStacksResponse>
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "1470",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:36:01.162Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <DeletionTime>2026-11-24T20:38:49.963Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000022</OperationId>
                            <OperationType>DELETE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackStatusReason>User Initiated</StackStatusReason>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>DELETE_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags/>
                      </member>
                    </Stacks>
                  </DescribeStacksResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000023</RequestId>
                  </ResponseMetadata>
                </DescribeStacksResponse>
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "1332",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:36:01.162Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <DeletionTime>2026-11-24T20:38:49.963Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000022</OperationId>
                            <OperationType>DELETE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>DELETE_COMPLETE</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags/>
                      </member>
                    </Stacks>
                  </DescribeStacksResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000024</RequestId>
                  </ResponseMetadata>
                </DescribeStacksResponse>
                """
            ),
        )
    )
    (
        controller.expect_operation("DescribeStackEvents")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "6311",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStackEventsResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStackEventsResult>
                    <StackEvents>
                      <member>
                        <EventId>00000000-0000-4000-8000-000000000017</EventId>
                        <PhysicalResourceId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</PhysicalResourceId>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <LogicalResourceId>aws-sdk-python-recorded-rollback-7ebfbcac</LogicalResourceId>
                        <ResourceStatus>ROLLBACK_COMPLETE</ResourceStatus>
                        <ClientRequestToken>00000000-0000-4000-8000-000000000003</ClientRequestToken>
                        <OperationId>00000000-0000-4000-8000-000000000005</OperationId>
                        <Timestamp>2026-11-24T20:38:36.483Z</Timestamp>
                        <ResourceType>AWS::CloudFormation::Stack</ResourceType>
                      </member>
                      <member>
                        <EventId>Queue-DELETE_COMPLETE-2026-11-24T20:38:36.155Z</EventId>
                        <PhysicalResourceId/>
                        <ResourceProperties>{&quot;QueueName&quot;:&quot;aws-sdk-python-recorded-invalid.fifo&quot;}</ResourceProperties>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <LogicalResourceId>Queue</LogicalResourceId>
                        <ResourceStatus>DELETE_COMPLETE</ResourceStatus>
                        <ClientRequestToken>00000000-0000-4000-8000-000000000003</ClientRequestToken>
                        <OperationId>00000000-0000-4000-8000-000000000005</OperationId>
                        <Timestamp>2026-11-24T20:38:36.155Z</Timestamp>
                        <ResourceType>AWS::SQS::Queue</ResourceType>
                      </member>
                      <member>
                        <EventId>00000000-0000-4000-8000-000000000018</EventId>
                        <PhysicalResourceId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</PhysicalResourceId>
                        <ResourceStatusReason>The following resource(s) failed to create: [Queue]. Rollback requested by user.</ResourceStatusReason>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <LogicalResourceId>aws-sdk-python-recorded-rollback-7ebfbcac</LogicalResourceId>
                        <ResourceStatus>ROLLBACK_IN_PROGRESS</ResourceStatus>
                        <ClientRequestToken>00000000-0000-4000-8000-000000000003</ClientRequestToken>
                        <OperationId>00000000-0000-4000-8000-000000000005</OperationId>
                        <Timestamp>2026-11-24T20:36:04.955Z</Timestamp>
                        <ResourceType>AWS::CloudFormation::Stack</ResourceType>
                      </member>
                      <member>
                        <EventId>Queue-CREATE_FAILED-2026-11-24T20:36:04.675Z</EventId>
                        <PhysicalResourceId/>
                        <ResourceStatusReason>Resource handler returned message: &quot;Can only include alphanumeric characters, hyphens, or underscores. 1 to 80 in length (Service: Sqs, Status Code: 400, Request ID: 00000000-0000-4000-8000-000000000019) (SDK Attempt Count: 1)&quot; (RequestToken: 02c244a4-4818-d489-9d1c-767bbd2ea8ce, HandlerErrorCode: GeneralServiceException)</ResourceStatusReason>
                        <ResourceProperties>{&quot;QueueName&quot;:&quot;aws-sdk-python-recorded-invalid.fifo&quot;}</ResourceProperties>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <LogicalResourceId>Queue</LogicalResourceId>
                        <ResourceStatus>CREATE_FAILED</ResourceStatus>
                        <ClientRequestToken>00000000-0000-4000-8000-000000000003</ClientRequestToken>
                        <OperationId>00000000-0000-4000-8000-000000000002</OperationId>
                        <Timestamp>2026-11-24T20:36:04.675Z</Timestamp>
                        <ResourceType>AWS::SQS::Queue</ResourceType>
                      </member>
                      <member>
                        <EventId>Queue-CREATE_IN_PROGRESS-2026-11-24T20:36:03.892Z</EventId>
                        <PhysicalResourceId/>
                        <ResourceProperties>{&quot;QueueName&quot;:&quot;aws-sdk-python-recorded-invalid.fifo&quot;}</ResourceProperties>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <LogicalResourceId>Queue</LogicalResourceId>
                        <ResourceStatus>CREATE_IN_PROGRESS</ResourceStatus>
                        <ClientRequestToken>00000000-0000-4000-8000-000000000003</ClientRequestToken>
                        <OperationId>00000000-0000-4000-8000-000000000002</OperationId>
                        <Timestamp>2026-11-24T20:36:03.892Z</Timestamp>
                        <ResourceType>AWS::SQS::Queue</ResourceType>
                      </member>
                      <member>
                        <EventId>00000000-0000-4000-8000-000000000002</EventId>
                        <PhysicalResourceId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</PhysicalResourceId>
                        <ResourceStatusReason>User Initiated</ResourceStatusReason>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-rollback-7ebfbcac/00000000-0000-4000-8000-000000000001</StackId>
                        <StackName>aws-sdk-python-recorded-rollback-7ebfbcac</StackName>
                        <LogicalResourceId>aws-sdk-python-recorded-rollback-7ebfbcac</LogicalResourceId>
                        <ResourceStatus>CREATE_IN_PROGRESS</ResourceStatus>
                        <ClientRequestToken>00000000-0000-4000-8000-000000000003</ClientRequestToken>
                        <OperationId>00000000-0000-4000-8000-000000000002</OperationId>
                        <Timestamp>2026-11-24T20:36:01.162Z</Timestamp>
                        <ResourceType>AWS::CloudFormation::Stack</ResourceType>
                      </member>
                    </StackEvents>
                  </DescribeStackEventsResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000020</RequestId>
                  </ResponseMetadata>
                </DescribeStackEventsResponse>
                """
            ),
        )
    )
    (
        controller.expect_operation("DeleteStack")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "211",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DeleteStackResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000021</RequestId>
                  </ResponseMetadata>
                </DeleteStackResponse>
                """
            ),
        )
    )
