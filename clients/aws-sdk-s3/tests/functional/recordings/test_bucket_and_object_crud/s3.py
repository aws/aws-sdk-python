# Recorded by smithy_test. Review it for anything identifying before committing.
from inspect import cleandoc

from smithy_test import HTTPMockController


def install(controller: HTTPMockController) -> None:
    (
        controller.expect_operation("CreateBucket")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "x-amz-id-2": "RECORDED-HOST-ID",
                "x-amz-request-id": "RECORDED-REQUEST-ID",
                "Server": "AmazonS3",
                "Location": "/aws-sdk-python-recorded-5e390e7d-111122223333-us-west-2-an",
                "x-amz-bucket-arn": "arn:aws:s3:::aws-sdk-python-recorded-5e390e7d-111122223333-us-west-2-an",
                "Content-Length": "0",
            },
            body=b"",
        )
    )
    (
        controller.expect_operation("HeadBucket")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "x-amz-id-2": "RECORDED-HOST-ID",
                "x-amz-request-id": "RECORDED-REQUEST-ID",
                "Server": "AmazonS3",
                "x-amz-bucket-region": "us-west-2",
                "x-amz-access-point-alias": "false",
                "x-amz-bucket-arn": "arn:aws:s3:::aws-sdk-python-recorded-5e390e7d-111122223333-us-west-2-an",
                "Content-Type": "application/xml",
                "Transfer-Encoding": "chunked",
            },
            body=b"",
        )
    )
    (
        controller.expect_operation("PutObject")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "x-amz-id-2": "RECORDED-HOST-ID",
                "x-amz-request-id": "RECORDED-REQUEST-ID",
                "Server": "AmazonS3",
                "x-amz-server-side-encryption": "AES256",
                "ETag": '"5d41402abc4b2a76b9719d911017c592"',
                "x-amz-checksum-crc64nvme": "M3eFcAZSQlc=",
                "x-amz-checksum-type": "FULL_OBJECT",
                "Content-Length": "0",
            },
            body=b"",
        )
    )
    (
        controller.expect_operation("GetObject")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "x-amz-request-id": "RECORDED-REQUEST-ID",
                "x-amz-id-2": "RECORDED-HOST-ID",
                "Content-Length": "5",
                "Accept-Ranges": "bytes",
                "Server": "AmazonS3",
                "Last-Modified": "Tue, 24 Nov 2026 19:04:14 GMT",
                "ETag": '"5d41402abc4b2a76b9719d911017c592"',
                "x-amz-checksum-crc64nvme": "M3eFcAZSQlc=",
                "x-amz-checksum-type": "FULL_OBJECT",
                "x-amz-meta-k": "v",
                "Content-Type": "application/octet-stream",
                "x-amz-server-side-encryption": "AES256",
            },
            body=b"hello",
        )
    )
    (
        controller.expect_operation("HeadObject")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "x-amz-id-2": "RECORDED-HOST-ID",
                "x-amz-request-id": "RECORDED-REQUEST-ID",
                "Server": "AmazonS3",
                "Last-Modified": "Tue, 24 Nov 2026 19:04:14 GMT",
                "ETag": '"5d41402abc4b2a76b9719d911017c592"',
                "x-amz-server-side-encryption": "AES256",
                "x-amz-meta-k": "v",
                "Accept-Ranges": "bytes",
                "Content-Length": "5",
                "Content-Type": "application/octet-stream",
            },
            body=b"",
        )
    )
    (
        controller.expect_operation("CopyObject")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "x-amz-id-2": "RECORDED-HOST-ID",
                "x-amz-request-id": "RECORDED-REQUEST-ID",
                "Server": "AmazonS3",
                "x-amz-server-side-encryption": "AES256",
                "Content-Length": "338",
                "Content-Type": "application/xml",
            },
            body=cleandoc(
                r"""
                <?xml version="1.0" encoding="UTF-8"?>
                <CopyObjectResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
                  <LastModified>2026-11-24T19:04:14.000Z</LastModified>
                  <ETag>&quot;5d41402abc4b2a76b9719d911017c592&quot;</ETag>
                  <ChecksumCRC64NVME>M3eFcAZSQlc=</ChecksumCRC64NVME>
                  <ChecksumType>FULL_OBJECT</ChecksumType>
                </CopyObjectResult>
                """
            ),
        )
    )
    (
        controller.expect_operation("ListObjectsV2")
        .times(2)
        .respond_with(
            status_code=200,
            headers={
                "x-amz-id-2": "RECORDED-HOST-ID",
                "x-amz-request-id": "RECORDED-REQUEST-ID",
                "Server": "AmazonS3",
                "x-amz-bucket-region": "us-west-2",
                "Content-Type": "application/xml",
                "Transfer-Encoding": "chunked",
            },
            body=cleandoc(
                r"""
                <?xml version="1.0" encoding="UTF-8"?>
                <ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
                  <Name>aws-sdk-python-recorded-5e390e7d-111122223333-us-west-2-an</Name>
                  <Prefix>a/</Prefix>
                  <KeyCount>2</KeyCount>
                  <MaxKeys>1000</MaxKeys>
                  <IsTruncated>false</IsTruncated>
                  <Contents>
                    <Key>a/1.txt</Key>
                    <LastModified>2026-11-24T19:04:14.000Z</LastModified>
                    <ETag>&quot;5d41402abc4b2a76b9719d911017c592&quot;</ETag>
                    <ChecksumAlgorithm>CRC64NVME</ChecksumAlgorithm>
                    <ChecksumType>FULL_OBJECT</ChecksumType>
                    <Size>5</Size>
                    <StorageClass>STANDARD</StorageClass>
                  </Contents>
                  <Contents>
                    <Key>a/2.txt</Key>
                    <LastModified>2026-11-24T19:04:14.000Z</LastModified>
                    <ETag>&quot;5d41402abc4b2a76b9719d911017c592&quot;</ETag>
                    <ChecksumAlgorithm>CRC64NVME</ChecksumAlgorithm>
                    <ChecksumType>FULL_OBJECT</ChecksumType>
                    <Size>5</Size>
                    <StorageClass>STANDARD</StorageClass>
                  </Contents>
                </ListBucketResult>
                """
            ),
        )
        .respond_with(
            status_code=200,
            headers={
                "x-amz-id-2": "RECORDED-HOST-ID",
                "x-amz-request-id": "RECORDED-REQUEST-ID",
                "Server": "AmazonS3",
                "x-amz-bucket-region": "us-west-2",
                "Content-Type": "application/xml",
                "Transfer-Encoding": "chunked",
            },
            body=cleandoc(
                r"""
                <?xml version="1.0" encoding="UTF-8"?>
                <ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
                  <Name>aws-sdk-python-recorded-5e390e7d-111122223333-us-west-2-an</Name>
                  <Prefix/>
                  <KeyCount>0</KeyCount>
                  <MaxKeys>1000</MaxKeys>
                  <IsTruncated>false</IsTruncated>
                </ListBucketResult>
                """
            ),
        )
    )
    (
        controller.expect_operation("DeleteObjects")
        .times(1)
        .respond_with(
            status_code=200,
            headers={
                "x-amz-id-2": "RECORDED-HOST-ID",
                "x-amz-request-id": "RECORDED-REQUEST-ID",
                "Server": "AmazonS3",
                "Connection": "close",
                "Content-Type": "application/xml",
                "Transfer-Encoding": "chunked",
            },
            body=cleandoc(
                r"""
                <?xml version="1.0" encoding="UTF-8"?>
                <DeleteResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
                  <Deleted>
                    <Key>a/2.txt</Key>
                  </Deleted>
                  <Deleted>
                    <Key>a/1.txt</Key>
                  </Deleted>
                </DeleteResult>
                """
            ),
        )
    )
    (
        controller.expect_operation("DeleteBucket")
        .times(1)
        .respond_with(
            status_code=204,
            headers={
                "x-amz-id-2": "RECORDED-HOST-ID",
                "x-amz-request-id": "RECORDED-REQUEST-ID",
                "Server": "AmazonS3",
            },
            body=b"",
        )
    )
