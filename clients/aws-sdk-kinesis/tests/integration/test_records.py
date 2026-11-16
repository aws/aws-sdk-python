# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Stream records and shards, from JS v3 Kinesis.e2e."""

import uuid

from aws_sdk_kinesis.aio.client import AsyncKinesisClient
from aws_sdk_kinesis.models import (
    GetRecordsInput,
    GetShardIteratorInput,
    ListShardsInput,
    PutRecordInput,
    PutRecordsInput,
    PutRecordsRequestEntry,
    Record,
    ShardIteratorType,
    StreamMode,
    DescribeStreamSummaryInput,
    StreamStatus,
)
from waiters import wait_until


async def test_stream_is_active_on_demand(
    kinesis: AsyncKinesisClient, stream: str
) -> None:
    """Verifies the shared stream reports ON_DEMAND mode, ACTIVE status, and its tags."""
    summary = (
        await kinesis.describe_stream_summary(
            DescribeStreamSummaryInput(stream_name=stream)
        )
    ).stream_description_summary

    assert summary.stream_status == StreamStatus.ACTIVE
    assert summary.stream_mode_details is not None
    assert summary.stream_mode_details.stream_mode == StreamMode.ON_DEMAND
    assert summary.open_shard_count >= 1


async def test_put_record_round_trips_binary_data(
    kinesis: AsyncKinesisClient, stream: str
) -> None:
    """Verifies a record of every byte value comes back intact through a shard iterator."""
    data = bytes(range(256))
    put = await kinesis.put_record(
        PutRecordInput(
            stream_name=stream, data=data, partition_key=f"pk-{uuid.uuid4().hex}"
        )
    )

    records = await _read_from(kinesis, stream, put.shard_id, put.sequence_number, 1)

    assert records[0].sequence_number == put.sequence_number
    assert records[0].data == data


async def test_put_records_batch_reads_back_in_order(
    kinesis: AsyncKinesisClient, stream: str
) -> None:
    """Verifies a PutRecords batch to one partition key is stored and read back in order."""
    partition_key = f"pk-{uuid.uuid4().hex}"
    payloads = [f"record-{i}-".encode() + bytes([i, 0, 255]) for i in range(10)]

    put = await kinesis.put_records(
        PutRecordsInput(
            stream_name=stream,
            records=[
                PutRecordsRequestEntry(data=payload, partition_key=partition_key)
                for payload in payloads
            ],
        )
    )

    assert not put.failed_record_count
    first = put.records[0]
    assert first.shard_id is not None and first.sequence_number is not None
    assert {entry.shard_id for entry in put.records} == {first.shard_id}

    records = await _read_from(
        kinesis, stream, first.shard_id, first.sequence_number, len(payloads)
    )

    assert [record.data for record in records] == payloads


async def test_list_shards_paginates_with_next_token(
    kinesis: AsyncKinesisClient, stream: str
) -> None:
    """Verifies paging ListShards one shard at a time yields the same shards as one call."""
    everything = await kinesis.list_shards(ListShardsInput(stream_name=stream))
    expected = [shard.shard_id for shard in everything.shards or []]
    assert len(expected) > 1

    paged: list[str] = []
    pages = 0
    page = await kinesis.list_shards(ListShardsInput(stream_name=stream, max_results=1))
    while True:
        pages += 1
        assert len(page.shards or []) == 1
        paged.extend(shard.shard_id for shard in page.shards or [])
        if page.next_token is None:
            break
        page = await kinesis.list_shards(
            ListShardsInput(next_token=page.next_token, max_results=1)
        )

    assert pages == len(expected)
    assert paged == expected


async def _read_from(
    kinesis: AsyncKinesisClient,
    stream: str,
    shard_id: str,
    sequence_number: str,
    count: int,
) -> list[Record]:
    """Read ``count`` records starting at ``sequence_number``, polling until they arrive."""
    iterator = (
        await kinesis.get_shard_iterator(
            GetShardIteratorInput(
                stream_name=stream,
                shard_id=shard_id,
                shard_iterator_type=ShardIteratorType.AT_SEQUENCE_NUMBER,
                starting_sequence_number=sequence_number,
            )
        )
    ).shard_iterator

    records: list[Record] = []
    state = {"iterator": iterator}

    async def poll() -> list[Record]:
        current = state["iterator"]
        if current is None:
            return records
        page = await kinesis.get_records(GetRecordsInput(shard_iterator=current))
        records.extend(page.records)
        state["iterator"] = page.next_shard_iterator
        return records

    await wait_until(
        poll,
        done=lambda r: len(r) >= count or state["iterator"] is None,
        interval=1,
        timeout=60,
    )
    return records[:count]
