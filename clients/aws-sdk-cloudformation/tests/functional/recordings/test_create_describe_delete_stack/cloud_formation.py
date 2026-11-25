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
                "Content-Length": "479",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <CreateStackResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <CreateStackResult>
                    <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-lifecycle-cc7dec8d/00000000-0000-4000-8000-000000000001</StackId>
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
        .times(12)
        .respond_with(
            status_code=200,
            headers={
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "Strict-Transport-Security": "max-age=47304000; includeSubDomains",
                "Cache-Control": "no-store, no-cache",
                "Content-Type": "text/xml",
                "Content-Length": "1775",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:30:53.434Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-lifecycle-cc7dec8d</StackName>
                        <Description>aws-sdk-python recorded test</Description>
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
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-lifecycle-cc7dec8d/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>CREATE_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags>
                          <member>
                            <Value>RecordedTest</Value>
                            <Key>Purpose</Key>
                          </member>
                        </Tags>
                        <Parameters>
                          <member>
                            <ParameterKey>Delay</ParameterKey>
                            <ParameterValue>1</ParameterValue>
                          </member>
                        </Parameters>
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
                "Content-Length": "1777",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:30:53.434Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-lifecycle-cc7dec8d</StackName>
                        <Description>aws-sdk-python recorded test</Description>
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
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-lifecycle-cc7dec8d/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>CREATE_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags>
                          <member>
                            <Value>RecordedTest</Value>
                            <Key>Purpose</Key>
                          </member>
                        </Tags>
                        <DetailedStatus>CONFIGURATION_COMPLETE</DetailedStatus>
                        <Parameters>
                          <member>
                            <ParameterKey>Delay</ParameterKey>
                            <ParameterValue>1</ParameterValue>
                          </member>
                        </Parameters>
                      </member>
                    </Stacks>
                  </DescribeStacksResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000005</RequestId>
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
                "Content-Length": "1777",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:30:53.434Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-lifecycle-cc7dec8d</StackName>
                        <Description>aws-sdk-python recorded test</Description>
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
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-lifecycle-cc7dec8d/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>CREATE_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags>
                          <member>
                            <Value>RecordedTest</Value>
                            <Key>Purpose</Key>
                          </member>
                        </Tags>
                        <DetailedStatus>CONFIGURATION_COMPLETE</DetailedStatus>
                        <Parameters>
                          <member>
                            <ParameterKey>Delay</ParameterKey>
                            <ParameterValue>1</ParameterValue>
                          </member>
                        </Parameters>
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
                "Content-Length": "1777",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:30:53.434Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-lifecycle-cc7dec8d</StackName>
                        <Description>aws-sdk-python recorded test</Description>
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
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-lifecycle-cc7dec8d/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>CREATE_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags>
                          <member>
                            <Value>RecordedTest</Value>
                            <Key>Purpose</Key>
                          </member>
                        </Tags>
                        <DetailedStatus>CONFIGURATION_COMPLETE</DetailedStatus>
                        <Parameters>
                          <member>
                            <ParameterKey>Delay</ParameterKey>
                            <ParameterValue>1</ParameterValue>
                          </member>
                        </Parameters>
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
                "Content-Length": "1777",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <CreationTime>2026-11-24T20:30:53.434Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-lifecycle-cc7dec8d</StackName>
                        <Description>aws-sdk-python recorded test</Description>
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
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-lifecycle-cc7dec8d/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>CREATE_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags>
                          <member>
                            <Value>RecordedTest</Value>
                            <Key>Purpose</Key>
                          </member>
                        </Tags>
                        <DetailedStatus>CONFIGURATION_COMPLETE</DetailedStatus>
                        <Parameters>
                          <member>
                            <ParameterKey>Delay</ParameterKey>
                            <ParameterValue>1</ParameterValue>
                          </member>
                        </Parameters>
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
                "Content-Length": "1980",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <Outputs>
                          <member>
                            <OutputKey>QueueUrl</OutputKey>
                            <OutputValue>https://sqs.us-west-2.amazonaws.com/123456789012/aws-sdk-python-recorded-lifecycle-cc7dec8d-Queue-Ww7ayLA31siU</OutputValue>
                          </member>
                        </Outputs>
                        <CreationTime>2026-11-24T20:30:53.434Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-lifecycle-cc7dec8d</StackName>
                        <Description>aws-sdk-python recorded test</Description>
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
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-lifecycle-cc7dec8d/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>CREATE_COMPLETE</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags>
                          <member>
                            <Value>RecordedTest</Value>
                            <Key>Purpose</Key>
                          </member>
                        </Tags>
                        <Parameters>
                          <member>
                            <ParameterKey>Delay</ParameterKey>
                            <ParameterValue>1</ParameterValue>
                          </member>
                        </Parameters>
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
                "Content-Length": "2107",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <Outputs>
                          <member>
                            <OutputKey>QueueUrl</OutputKey>
                            <OutputValue>https://sqs.us-west-2.amazonaws.com/123456789012/aws-sdk-python-recorded-lifecycle-cc7dec8d-Queue-Ww7ayLA31siU</OutputValue>
                          </member>
                        </Outputs>
                        <CreationTime>2026-11-24T20:30:53.434Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-lifecycle-cc7dec8d</StackName>
                        <Description>aws-sdk-python recorded test</Description>
                        <DeletionTime>2026-11-24T20:32:10.287Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000011</OperationId>
                            <OperationType>DELETE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackStatusReason>User Initiated</StackStatusReason>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-lifecycle-cc7dec8d/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>DELETE_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags>
                          <member>
                            <Value>RecordedTest</Value>
                            <Key>Purpose</Key>
                          </member>
                        </Tags>
                        <Parameters>
                          <member>
                            <ParameterKey>Delay</ParameterKey>
                            <ParameterValue>1</ParameterValue>
                          </member>
                        </Parameters>
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
                "Content-Length": "2045",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <Outputs>
                          <member>
                            <OutputKey>QueueUrl</OutputKey>
                            <OutputValue>https://sqs.us-west-2.amazonaws.com/123456789012/aws-sdk-python-recorded-lifecycle-cc7dec8d-Queue-Ww7ayLA31siU</OutputValue>
                          </member>
                        </Outputs>
                        <CreationTime>2026-11-24T20:30:53.434Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-lifecycle-cc7dec8d</StackName>
                        <Description>aws-sdk-python recorded test</Description>
                        <DeletionTime>2026-11-24T20:32:10.287Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000011</OperationId>
                            <OperationType>DELETE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-lifecycle-cc7dec8d/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>DELETE_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags>
                          <member>
                            <Value>RecordedTest</Value>
                            <Key>Purpose</Key>
                          </member>
                        </Tags>
                        <Parameters>
                          <member>
                            <ParameterKey>Delay</ParameterKey>
                            <ParameterValue>1</ParameterValue>
                          </member>
                        </Parameters>
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
                "Content-Length": "2045",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <Outputs>
                          <member>
                            <OutputKey>QueueUrl</OutputKey>
                            <OutputValue>https://sqs.us-west-2.amazonaws.com/123456789012/aws-sdk-python-recorded-lifecycle-cc7dec8d-Queue-Ww7ayLA31siU</OutputValue>
                          </member>
                        </Outputs>
                        <CreationTime>2026-11-24T20:30:53.434Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-lifecycle-cc7dec8d</StackName>
                        <Description>aws-sdk-python recorded test</Description>
                        <DeletionTime>2026-11-24T20:32:10.287Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000011</OperationId>
                            <OperationType>DELETE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-lifecycle-cc7dec8d/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>DELETE_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags>
                          <member>
                            <Value>RecordedTest</Value>
                            <Key>Purpose</Key>
                          </member>
                        </Tags>
                        <Parameters>
                          <member>
                            <ParameterKey>Delay</ParameterKey>
                            <ParameterValue>1</ParameterValue>
                          </member>
                        </Parameters>
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
                "Content-Length": "2045",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <Outputs>
                          <member>
                            <OutputKey>QueueUrl</OutputKey>
                            <OutputValue>https://sqs.us-west-2.amazonaws.com/123456789012/aws-sdk-python-recorded-lifecycle-cc7dec8d-Queue-Ww7ayLA31siU</OutputValue>
                          </member>
                        </Outputs>
                        <CreationTime>2026-11-24T20:30:53.434Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-lifecycle-cc7dec8d</StackName>
                        <Description>aws-sdk-python recorded test</Description>
                        <DeletionTime>2026-11-24T20:32:10.287Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000011</OperationId>
                            <OperationType>DELETE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-lifecycle-cc7dec8d/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>DELETE_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags>
                          <member>
                            <Value>RecordedTest</Value>
                            <Key>Purpose</Key>
                          </member>
                        </Tags>
                        <Parameters>
                          <member>
                            <ParameterKey>Delay</ParameterKey>
                            <ParameterValue>1</ParameterValue>
                          </member>
                        </Parameters>
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
                "Content-Length": "2045",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <Outputs>
                          <member>
                            <OutputKey>QueueUrl</OutputKey>
                            <OutputValue>https://sqs.us-west-2.amazonaws.com/123456789012/aws-sdk-python-recorded-lifecycle-cc7dec8d-Queue-Ww7ayLA31siU</OutputValue>
                          </member>
                        </Outputs>
                        <CreationTime>2026-11-24T20:30:53.434Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-lifecycle-cc7dec8d</StackName>
                        <Description>aws-sdk-python recorded test</Description>
                        <DeletionTime>2026-11-24T20:32:10.287Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000011</OperationId>
                            <OperationType>DELETE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <EnableTerminationProtection>false</EnableTerminationProtection>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-lifecycle-cc7dec8d/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>DELETE_IN_PROGRESS</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags>
                          <member>
                            <Value>RecordedTest</Value>
                            <Key>Purpose</Key>
                          </member>
                        </Tags>
                        <Parameters>
                          <member>
                            <ParameterKey>Delay</ParameterKey>
                            <ParameterValue>1</ParameterValue>
                          </member>
                        </Parameters>
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
                "Content-Length": "1969",
                "connection": "keep-alive",
            },
            body=cleandoc(
                r"""
                <DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
                  <DescribeStacksResult>
                    <Stacks>
                      <member>
                        <Outputs>
                          <member>
                            <OutputKey>QueueUrl</OutputKey>
                            <OutputValue>https://sqs.us-west-2.amazonaws.com/123456789012/aws-sdk-python-recorded-lifecycle-cc7dec8d-Queue-Ww7ayLA31siU</OutputValue>
                          </member>
                        </Outputs>
                        <CreationTime>2026-11-24T20:30:53.434Z</CreationTime>
                        <NotificationARNs/>
                        <StackName>aws-sdk-python-recorded-lifecycle-cc7dec8d</StackName>
                        <Description>aws-sdk-python recorded test</Description>
                        <DeletionTime>2026-11-24T20:32:10.287Z</DeletionTime>
                        <DeploymentConfig>
                          <Mode>STANDARD</Mode>
                          <DisableRollback>false</DisableRollback>
                        </DeploymentConfig>
                        <RollbackConfiguration/>
                        <LastOperations>
                          <member>
                            <OperationId>00000000-0000-4000-8000-000000000011</OperationId>
                            <OperationType>DELETE_STACK</OperationType>
                          </member>
                        </LastOperations>
                        <DriftInformation>
                          <StackDriftStatus>NOT_CHECKED</StackDriftStatus>
                        </DriftInformation>
                        <StackId>arn:aws:cloudformation:us-west-2:123456789012:stack/aws-sdk-python-recorded-lifecycle-cc7dec8d/00000000-0000-4000-8000-000000000001</StackId>
                        <StackStatus>DELETE_COMPLETE</StackStatus>
                        <DisableRollback>false</DisableRollback>
                        <Tags>
                          <member>
                            <Value>RecordedTest</Value>
                            <Key>Purpose</Key>
                          </member>
                        </Tags>
                        <Parameters>
                          <member>
                            <ParameterKey>Delay</ParameterKey>
                            <ParameterValue>1</ParameterValue>
                          </member>
                        </Parameters>
                      </member>
                    </Stacks>
                  </DescribeStacksResult>
                  <ResponseMetadata>
                    <RequestId>00000000-0000-4000-8000-000000000017</RequestId>
                  </ResponseMetadata>
                </DescribeStacksResponse>
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
                    <RequestId>00000000-0000-4000-8000-000000000010</RequestId>
                  </ResponseMetadata>
                </DeleteStackResponse>
                """
            ),
        )
    )
