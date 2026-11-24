# Recorded by smithy_test. Review it for anything identifying before committing.
from inspect import cleandoc

from smithy_test import HTTPMockController


def install(controller: HTTPMockController) -> None:
    (
        controller.expect_operation("CreateTable")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "901",
                "Connection": "keep-alive",
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "517962360",
            },
            body=cleandoc(
                r"""
                {
                  "TableDescription": {
                    "AttributeDefinitions": [
                      {
                        "AttributeName": "id",
                        "AttributeType": "S"
                      }
                    ],
                    "BillingModeSummary": {
                      "BillingMode": "PAY_PER_REQUEST"
                    },
                    "CreationDateTime": 1795547063.215,
                    "DeletionProtectionEnabled": false,
                    "ItemCount": 0,
                    "KeySchema": [
                      {
                        "AttributeName": "id",
                        "KeyType": "HASH"
                      }
                    ],
                    "ProvisionedThroughput": {
                      "NumberOfDecreasesToday": 0,
                      "ReadCapacityUnits": 0,
                      "WriteCapacityUnits": 0
                    },
                    "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/aws-sdk-python-recorded-fe642932",
                    "TableId": "00000000-0000-4000-8000-000000000001",
                    "TableName": "aws-sdk-python-recorded-fe642932",
                    "TableSizeBytes": 0,
                    "TableStatus": "CREATING",
                    "TableThroughputModeSummary": {
                      "TableThroughputMode": "PAY_PER_REQUEST"
                    }
                  }
                }
                """
            ),
        )
    )
    (
        controller.expect_operation("DescribeTable")
        .times(14)
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "890",
                "Connection": "keep-alive",
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2565307401",
            },
            body=cleandoc(
                r"""
                {
                  "Table": {
                    "AttributeDefinitions": [
                      {
                        "AttributeName": "id",
                        "AttributeType": "S"
                      }
                    ],
                    "BillingModeSummary": {
                      "BillingMode": "PAY_PER_REQUEST"
                    },
                    "CreationDateTime": 1795547063.215,
                    "DeletionProtectionEnabled": false,
                    "ItemCount": 0,
                    "KeySchema": [
                      {
                        "AttributeName": "id",
                        "KeyType": "HASH"
                      }
                    ],
                    "ProvisionedThroughput": {
                      "NumberOfDecreasesToday": 0,
                      "ReadCapacityUnits": 0,
                      "WriteCapacityUnits": 0
                    },
                    "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/aws-sdk-python-recorded-fe642932",
                    "TableId": "00000000-0000-4000-8000-000000000001",
                    "TableName": "aws-sdk-python-recorded-fe642932",
                    "TableSizeBytes": 0,
                    "TableStatus": "CREATING",
                    "TableThroughputModeSummary": {
                      "TableThroughputMode": "PAY_PER_REQUEST"
                    }
                  }
                }
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "890",
                "Connection": "keep-alive",
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2565307401",
            },
            body=cleandoc(
                r"""
                {
                  "Table": {
                    "AttributeDefinitions": [
                      {
                        "AttributeName": "id",
                        "AttributeType": "S"
                      }
                    ],
                    "BillingModeSummary": {
                      "BillingMode": "PAY_PER_REQUEST"
                    },
                    "CreationDateTime": 1795547063.215,
                    "DeletionProtectionEnabled": false,
                    "ItemCount": 0,
                    "KeySchema": [
                      {
                        "AttributeName": "id",
                        "KeyType": "HASH"
                      }
                    ],
                    "ProvisionedThroughput": {
                      "NumberOfDecreasesToday": 0,
                      "ReadCapacityUnits": 0,
                      "WriteCapacityUnits": 0
                    },
                    "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/aws-sdk-python-recorded-fe642932",
                    "TableId": "00000000-0000-4000-8000-000000000001",
                    "TableName": "aws-sdk-python-recorded-fe642932",
                    "TableSizeBytes": 0,
                    "TableStatus": "CREATING",
                    "TableThroughputModeSummary": {
                      "TableThroughputMode": "PAY_PER_REQUEST"
                    }
                  }
                }
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "890",
                "Connection": "keep-alive",
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2565307401",
            },
            body=cleandoc(
                r"""
                {
                  "Table": {
                    "AttributeDefinitions": [
                      {
                        "AttributeName": "id",
                        "AttributeType": "S"
                      }
                    ],
                    "BillingModeSummary": {
                      "BillingMode": "PAY_PER_REQUEST"
                    },
                    "CreationDateTime": 1795547063.215,
                    "DeletionProtectionEnabled": false,
                    "ItemCount": 0,
                    "KeySchema": [
                      {
                        "AttributeName": "id",
                        "KeyType": "HASH"
                      }
                    ],
                    "ProvisionedThroughput": {
                      "NumberOfDecreasesToday": 0,
                      "ReadCapacityUnits": 0,
                      "WriteCapacityUnits": 0
                    },
                    "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/aws-sdk-python-recorded-fe642932",
                    "TableId": "00000000-0000-4000-8000-000000000001",
                    "TableName": "aws-sdk-python-recorded-fe642932",
                    "TableSizeBytes": 0,
                    "TableStatus": "CREATING",
                    "TableThroughputModeSummary": {
                      "TableThroughputMode": "PAY_PER_REQUEST"
                    }
                  }
                }
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "890",
                "Connection": "keep-alive",
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2565307401",
            },
            body=cleandoc(
                r"""
                {
                  "Table": {
                    "AttributeDefinitions": [
                      {
                        "AttributeName": "id",
                        "AttributeType": "S"
                      }
                    ],
                    "BillingModeSummary": {
                      "BillingMode": "PAY_PER_REQUEST"
                    },
                    "CreationDateTime": 1795547063.215,
                    "DeletionProtectionEnabled": false,
                    "ItemCount": 0,
                    "KeySchema": [
                      {
                        "AttributeName": "id",
                        "KeyType": "HASH"
                      }
                    ],
                    "ProvisionedThroughput": {
                      "NumberOfDecreasesToday": 0,
                      "ReadCapacityUnits": 0,
                      "WriteCapacityUnits": 0
                    },
                    "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/aws-sdk-python-recorded-fe642932",
                    "TableId": "00000000-0000-4000-8000-000000000001",
                    "TableName": "aws-sdk-python-recorded-fe642932",
                    "TableSizeBytes": 0,
                    "TableStatus": "CREATING",
                    "TableThroughputModeSummary": {
                      "TableThroughputMode": "PAY_PER_REQUEST"
                    }
                  }
                }
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "890",
                "Connection": "keep-alive",
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2565307401",
            },
            body=cleandoc(
                r"""
                {
                  "Table": {
                    "AttributeDefinitions": [
                      {
                        "AttributeName": "id",
                        "AttributeType": "S"
                      }
                    ],
                    "BillingModeSummary": {
                      "BillingMode": "PAY_PER_REQUEST"
                    },
                    "CreationDateTime": 1795547063.215,
                    "DeletionProtectionEnabled": false,
                    "ItemCount": 0,
                    "KeySchema": [
                      {
                        "AttributeName": "id",
                        "KeyType": "HASH"
                      }
                    ],
                    "ProvisionedThroughput": {
                      "NumberOfDecreasesToday": 0,
                      "ReadCapacityUnits": 0,
                      "WriteCapacityUnits": 0
                    },
                    "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/aws-sdk-python-recorded-fe642932",
                    "TableId": "00000000-0000-4000-8000-000000000001",
                    "TableName": "aws-sdk-python-recorded-fe642932",
                    "TableSizeBytes": 0,
                    "TableStatus": "CREATING",
                    "TableThroughputModeSummary": {
                      "TableThroughputMode": "PAY_PER_REQUEST"
                    }
                  }
                }
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "890",
                "Connection": "keep-alive",
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2565307401",
            },
            body=cleandoc(
                r"""
                {
                  "Table": {
                    "AttributeDefinitions": [
                      {
                        "AttributeName": "id",
                        "AttributeType": "S"
                      }
                    ],
                    "BillingModeSummary": {
                      "BillingMode": "PAY_PER_REQUEST"
                    },
                    "CreationDateTime": 1795547063.215,
                    "DeletionProtectionEnabled": false,
                    "ItemCount": 0,
                    "KeySchema": [
                      {
                        "AttributeName": "id",
                        "KeyType": "HASH"
                      }
                    ],
                    "ProvisionedThroughput": {
                      "NumberOfDecreasesToday": 0,
                      "ReadCapacityUnits": 0,
                      "WriteCapacityUnits": 0
                    },
                    "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/aws-sdk-python-recorded-fe642932",
                    "TableId": "00000000-0000-4000-8000-000000000001",
                    "TableName": "aws-sdk-python-recorded-fe642932",
                    "TableSizeBytes": 0,
                    "TableStatus": "CREATING",
                    "TableThroughputModeSummary": {
                      "TableThroughputMode": "PAY_PER_REQUEST"
                    }
                  }
                }
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "890",
                "Connection": "keep-alive",
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2565307401",
            },
            body=cleandoc(
                r"""
                {
                  "Table": {
                    "AttributeDefinitions": [
                      {
                        "AttributeName": "id",
                        "AttributeType": "S"
                      }
                    ],
                    "BillingModeSummary": {
                      "BillingMode": "PAY_PER_REQUEST"
                    },
                    "CreationDateTime": 1795547063.215,
                    "DeletionProtectionEnabled": false,
                    "ItemCount": 0,
                    "KeySchema": [
                      {
                        "AttributeName": "id",
                        "KeyType": "HASH"
                      }
                    ],
                    "ProvisionedThroughput": {
                      "NumberOfDecreasesToday": 0,
                      "ReadCapacityUnits": 0,
                      "WriteCapacityUnits": 0
                    },
                    "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/aws-sdk-python-recorded-fe642932",
                    "TableId": "00000000-0000-4000-8000-000000000001",
                    "TableName": "aws-sdk-python-recorded-fe642932",
                    "TableSizeBytes": 0,
                    "TableStatus": "CREATING",
                    "TableThroughputModeSummary": {
                      "TableThroughputMode": "PAY_PER_REQUEST"
                    }
                  }
                }
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "890",
                "Connection": "keep-alive",
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2565307401",
            },
            body=cleandoc(
                r"""
                {
                  "Table": {
                    "AttributeDefinitions": [
                      {
                        "AttributeName": "id",
                        "AttributeType": "S"
                      }
                    ],
                    "BillingModeSummary": {
                      "BillingMode": "PAY_PER_REQUEST"
                    },
                    "CreationDateTime": 1795547063.215,
                    "DeletionProtectionEnabled": false,
                    "ItemCount": 0,
                    "KeySchema": [
                      {
                        "AttributeName": "id",
                        "KeyType": "HASH"
                      }
                    ],
                    "ProvisionedThroughput": {
                      "NumberOfDecreasesToday": 0,
                      "ReadCapacityUnits": 0,
                      "WriteCapacityUnits": 0
                    },
                    "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/aws-sdk-python-recorded-fe642932",
                    "TableId": "00000000-0000-4000-8000-000000000001",
                    "TableName": "aws-sdk-python-recorded-fe642932",
                    "TableSizeBytes": 0,
                    "TableStatus": "CREATING",
                    "TableThroughputModeSummary": {
                      "TableThroughputMode": "PAY_PER_REQUEST"
                    }
                  }
                }
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "890",
                "Connection": "keep-alive",
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2565307401",
            },
            body=cleandoc(
                r"""
                {
                  "Table": {
                    "AttributeDefinitions": [
                      {
                        "AttributeName": "id",
                        "AttributeType": "S"
                      }
                    ],
                    "BillingModeSummary": {
                      "BillingMode": "PAY_PER_REQUEST"
                    },
                    "CreationDateTime": 1795547063.215,
                    "DeletionProtectionEnabled": false,
                    "ItemCount": 0,
                    "KeySchema": [
                      {
                        "AttributeName": "id",
                        "KeyType": "HASH"
                      }
                    ],
                    "ProvisionedThroughput": {
                      "NumberOfDecreasesToday": 0,
                      "ReadCapacityUnits": 0,
                      "WriteCapacityUnits": 0
                    },
                    "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/aws-sdk-python-recorded-fe642932",
                    "TableId": "00000000-0000-4000-8000-000000000001",
                    "TableName": "aws-sdk-python-recorded-fe642932",
                    "TableSizeBytes": 0,
                    "TableStatus": "CREATING",
                    "TableThroughputModeSummary": {
                      "TableThroughputMode": "PAY_PER_REQUEST"
                    }
                  }
                }
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "890",
                "Connection": "keep-alive",
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2565307401",
            },
            body=cleandoc(
                r"""
                {
                  "Table": {
                    "AttributeDefinitions": [
                      {
                        "AttributeName": "id",
                        "AttributeType": "S"
                      }
                    ],
                    "BillingModeSummary": {
                      "BillingMode": "PAY_PER_REQUEST"
                    },
                    "CreationDateTime": 1795547063.215,
                    "DeletionProtectionEnabled": false,
                    "ItemCount": 0,
                    "KeySchema": [
                      {
                        "AttributeName": "id",
                        "KeyType": "HASH"
                      }
                    ],
                    "ProvisionedThroughput": {
                      "NumberOfDecreasesToday": 0,
                      "ReadCapacityUnits": 0,
                      "WriteCapacityUnits": 0
                    },
                    "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/aws-sdk-python-recorded-fe642932",
                    "TableId": "00000000-0000-4000-8000-000000000001",
                    "TableName": "aws-sdk-python-recorded-fe642932",
                    "TableSizeBytes": 0,
                    "TableStatus": "CREATING",
                    "TableThroughputModeSummary": {
                      "TableThroughputMode": "PAY_PER_REQUEST"
                    }
                  }
                }
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "890",
                "Connection": "keep-alive",
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2565307401",
            },
            body=cleandoc(
                r"""
                {
                  "Table": {
                    "AttributeDefinitions": [
                      {
                        "AttributeName": "id",
                        "AttributeType": "S"
                      }
                    ],
                    "BillingModeSummary": {
                      "BillingMode": "PAY_PER_REQUEST"
                    },
                    "CreationDateTime": 1795547063.215,
                    "DeletionProtectionEnabled": false,
                    "ItemCount": 0,
                    "KeySchema": [
                      {
                        "AttributeName": "id",
                        "KeyType": "HASH"
                      }
                    ],
                    "ProvisionedThroughput": {
                      "NumberOfDecreasesToday": 0,
                      "ReadCapacityUnits": 0,
                      "WriteCapacityUnits": 0
                    },
                    "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/aws-sdk-python-recorded-fe642932",
                    "TableId": "00000000-0000-4000-8000-000000000001",
                    "TableName": "aws-sdk-python-recorded-fe642932",
                    "TableSizeBytes": 0,
                    "TableStatus": "CREATING",
                    "TableThroughputModeSummary": {
                      "TableThroughputMode": "PAY_PER_REQUEST"
                    }
                  }
                }
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "890",
                "Connection": "keep-alive",
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2565307401",
            },
            body=cleandoc(
                r"""
                {
                  "Table": {
                    "AttributeDefinitions": [
                      {
                        "AttributeName": "id",
                        "AttributeType": "S"
                      }
                    ],
                    "BillingModeSummary": {
                      "BillingMode": "PAY_PER_REQUEST"
                    },
                    "CreationDateTime": 1795547063.215,
                    "DeletionProtectionEnabled": false,
                    "ItemCount": 0,
                    "KeySchema": [
                      {
                        "AttributeName": "id",
                        "KeyType": "HASH"
                      }
                    ],
                    "ProvisionedThroughput": {
                      "NumberOfDecreasesToday": 0,
                      "ReadCapacityUnits": 0,
                      "WriteCapacityUnits": 0
                    },
                    "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/aws-sdk-python-recorded-fe642932",
                    "TableId": "00000000-0000-4000-8000-000000000001",
                    "TableName": "aws-sdk-python-recorded-fe642932",
                    "TableSizeBytes": 0,
                    "TableStatus": "CREATING",
                    "TableThroughputModeSummary": {
                      "TableThroughputMode": "PAY_PER_REQUEST"
                    }
                  }
                }
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "890",
                "Connection": "keep-alive",
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2565307401",
            },
            body=cleandoc(
                r"""
                {
                  "Table": {
                    "AttributeDefinitions": [
                      {
                        "AttributeName": "id",
                        "AttributeType": "S"
                      }
                    ],
                    "BillingModeSummary": {
                      "BillingMode": "PAY_PER_REQUEST"
                    },
                    "CreationDateTime": 1795547063.215,
                    "DeletionProtectionEnabled": false,
                    "ItemCount": 0,
                    "KeySchema": [
                      {
                        "AttributeName": "id",
                        "KeyType": "HASH"
                      }
                    ],
                    "ProvisionedThroughput": {
                      "NumberOfDecreasesToday": 0,
                      "ReadCapacityUnits": 0,
                      "WriteCapacityUnits": 0
                    },
                    "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/aws-sdk-python-recorded-fe642932",
                    "TableId": "00000000-0000-4000-8000-000000000001",
                    "TableName": "aws-sdk-python-recorded-fe642932",
                    "TableSizeBytes": 0,
                    "TableStatus": "CREATING",
                    "TableThroughputModeSummary": {
                      "TableThroughputMode": "PAY_PER_REQUEST"
                    }
                  }
                }
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "1132",
                "Connection": "keep-alive",
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "780005708",
            },
            body=cleandoc(
                r"""
                {
                  "Table": {
                    "AttributeDefinitions": [
                      {
                        "AttributeName": "id",
                        "AttributeType": "S"
                      }
                    ],
                    "BillingModeSummary": {
                      "BillingMode": "PAY_PER_REQUEST",
                      "LastUpdateToPayPerRequestDateTime": 1795547063.215
                    },
                    "CreationDateTime": 1795547063.215,
                    "DeletionProtectionEnabled": false,
                    "ItemCount": 0,
                    "KeySchema": [
                      {
                        "AttributeName": "id",
                        "KeyType": "HASH"
                      }
                    ],
                    "ProvisionedThroughput": {
                      "NumberOfDecreasesToday": 0,
                      "ReadCapacityUnits": 0,
                      "WriteCapacityUnits": 0
                    },
                    "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/aws-sdk-python-recorded-fe642932",
                    "TableId": "00000000-0000-4000-8000-000000000001",
                    "TableName": "aws-sdk-python-recorded-fe642932",
                    "TableSizeBytes": 0,
                    "TableStatus": "ACTIVE",
                    "TableThroughputModeSummary": {
                      "LastUpdateToPayPerRequestDateTime": 1795547063.215,
                      "TableThroughputMode": "PAY_PER_REQUEST"
                    },
                    "WarmThroughput": {
                      "ReadUnitsPerSecond": 12000,
                      "Status": "ACTIVE",
                      "WriteUnitsPerSecond": 4000
                    }
                  }
                }
                """
            ),
        )
    )
    (
        controller.expect_operation("PutItem")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "2",
                "Connection": "keep-alive",
                "x-amzn-requestid": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2745614147",
            },
            body=cleandoc(
                r"""
                {}
                """
            ),
        )
    )
    (
        controller.expect_operation("GetItem")
        .times(3)
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "304",
                "Connection": "keep-alive",
                "x-amzn-requestid": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "3462548770",
            },
            body=cleandoc(
                r"""
                {
                  "Item": {
                    "count": {
                      "N": "1"
                    },
                    "id": {
                      "S": "a"
                    },
                    "tags": {
                      "SS": [
                        "x",
                        "y"
                      ]
                    },
                    "profile": {
                      "M": {
                        "admin": {
                          "BOOL": true
                        },
                        "name": {
                          "S": "Ann"
                        }
                      }
                    }
                  }
                }
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "304",
                "Connection": "keep-alive",
                "x-amzn-requestid": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2515338361",
            },
            body=cleandoc(
                r"""
                {
                  "Item": {
                    "count": {
                      "N": "2"
                    },
                    "id": {
                      "S": "a"
                    },
                    "profile": {
                      "M": {
                        "admin": {
                          "BOOL": true
                        },
                        "name": {
                          "S": "Ann"
                        }
                      }
                    },
                    "tags": {
                      "SS": [
                        "x",
                        "y"
                      ]
                    }
                  }
                }
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "2",
                "Connection": "keep-alive",
                "x-amzn-requestid": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2745614147",
            },
            body=cleandoc(
                r"""
                {}
                """
            ),
        )
    )
    (
        controller.expect_operation("UpdateItem")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "2",
                "Connection": "keep-alive",
                "x-amzn-requestid": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2745614147",
            },
            body=cleandoc(
                r"""
                {}
                """
            ),
        )
    )
    (
        controller.expect_operation("Scan")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "396",
                "Connection": "keep-alive",
                "x-amzn-requestid": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "3072308734",
            },
            body=cleandoc(
                r"""
                {
                  "Count": 1,
                  "Items": [
                    {
                      "count": {
                        "N": "2"
                      },
                      "id": {
                        "S": "a"
                      },
                      "profile": {
                        "M": {
                          "admin": {
                            "BOOL": true
                          },
                          "name": {
                            "S": "Ann"
                          }
                        }
                      },
                      "tags": {
                        "SS": [
                          "x",
                          "y"
                        ]
                      }
                    }
                  ],
                  "ScannedCount": 1
                }
                """
            ),
        )
    )
    (
        controller.expect_operation("DeleteItem")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "2",
                "Connection": "keep-alive",
                "x-amzn-requestid": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "2745614147",
            },
            body=cleandoc(
                r"""
                {}
                """
            ),
        )
    )
    (
        controller.expect_operation("DeleteTable")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "Server": "Server",
                "Content-Type": "application/x-amz-json-1.0",
                "Content-Length": "767",
                "Connection": "keep-alive",
                "x-amzn-RequestId": "RECORDED-REQUEST-ID",
                "x-amz-crc32": "1511882710",
            },
            body=cleandoc(
                r"""
                {
                  "TableDescription": {
                    "BillingModeSummary": {
                      "BillingMode": "PAY_PER_REQUEST",
                      "LastUpdateToPayPerRequestDateTime": 1795547063.215
                    },
                    "DeletionProtectionEnabled": false,
                    "ItemCount": 0,
                    "ProvisionedThroughput": {
                      "NumberOfDecreasesToday": 0,
                      "ReadCapacityUnits": 0,
                      "WriteCapacityUnits": 0
                    },
                    "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/aws-sdk-python-recorded-fe642932",
                    "TableId": "00000000-0000-4000-8000-000000000001",
                    "TableName": "aws-sdk-python-recorded-fe642932",
                    "TableSizeBytes": 0,
                    "TableStatus": "DELETING",
                    "TableThroughputModeSummary": {
                      "LastUpdateToPayPerRequestDateTime": 1795547063.215,
                      "TableThroughputMode": "PAY_PER_REQUEST"
                    }
                  }
                }
                """
            ),
        )
    )
