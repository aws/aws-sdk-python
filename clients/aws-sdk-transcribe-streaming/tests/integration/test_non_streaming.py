# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test non-streaming output type handling using Medical Scribe."""

import asyncio
import time
import uuid

from smithy_core.exceptions import CallError
from smithy_http.aio.crt import AWSCRTHTTPClient

from aws_sdk_transcribe_streaming.models import (
    BadRequestException,
    ClinicalNoteGenerationSettings,
    GetMedicalScribeStreamOutput,
    LanguageCode,
    LimitExceededException,
    MediaEncoding,
    MedicalScribeAudioEvent,
    MedicalScribeConfigurationEvent,
    MedicalScribeInputStreamAudioEvent,
    MedicalScribeInputStreamConfigurationEvent,
    MedicalScribeInputStreamSessionControlEvent,
    MedicalScribePostStreamAnalyticsSettings,
    MedicalScribeSessionControlEvent,
    MedicalScribeSessionControlEventType,
)

from . import AUDIO_FILE, create_transcribe_client

SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2
CHANNEL_NUMS = 1
CHUNK_SIZE = 1024 * 8

# Maximum time to wait for IAM role propagation across services.
ROLE_PROPAGATION_TIMEOUT = 300
# Delay between retries while waiting for IAM role propagation.
ROLE_PROPAGATION_RETRY_DELAY = 5


async def _run_medical_scribe_session(role_arn: str, s3_bucket: str) -> None:
    """Run a full Medical Scribe streaming session and verify its completion."""
    async with await create_transcribe_client(
        "us-east-1", transport=AWSCRTHTTPClient()
    ) as transcribe_client:
        session_id = str(uuid.uuid4())

        stream = await transcribe_client.start_medical_scribe_stream(
            language_code=LanguageCode.EN_US,
            media_sample_rate_hertz=SAMPLE_RATE,
            media_encoding=MediaEncoding.PCM,
            session_id=session_id,
        )

        await stream.input_stream.send(
            MedicalScribeInputStreamConfigurationEvent(
                value=MedicalScribeConfigurationEvent(
                    resource_access_role_arn=role_arn,
                    post_stream_analytics_settings=MedicalScribePostStreamAnalyticsSettings(
                        clinical_note_generation_settings=ClinicalNoteGenerationSettings(
                            output_bucket_name=s3_bucket
                        )
                    ),
                )
            )
        )

        start_time = time.time()
        elapsed_audio_time = 0.0

        with AUDIO_FILE.open("rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                await stream.input_stream.send(
                    MedicalScribeInputStreamAudioEvent(
                        value=MedicalScribeAudioEvent(audio_chunk=chunk)
                    )
                )
                elapsed_audio_time += len(chunk) / (
                    BYTES_PER_SAMPLE * SAMPLE_RATE * CHANNEL_NUMS
                )
                wait_time = start_time + elapsed_audio_time - time.time()
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

        await stream.input_stream.send(
            MedicalScribeInputStreamSessionControlEvent(
                value=MedicalScribeSessionControlEvent(
                    type=MedicalScribeSessionControlEventType.END_OF_SESSION
                )
            )
        )
        await stream.input_stream.close()

        await stream.await_output()

        # Consume output stream events to properly close the connection
        if stream.output_stream:
            async for _ in stream.output_stream:
                pass

        response = await transcribe_client.get_medical_scribe_stream(
            session_id=session_id
        )

        assert isinstance(response, GetMedicalScribeStreamOutput)
        assert response.medical_scribe_stream_details is not None

        details = response.medical_scribe_stream_details
        assert details.session_id == session_id
        assert details.stream_status == "COMPLETED"
        assert details.language_code == "en-US"
        assert details.media_encoding == "pcm"
        assert details.media_sample_rate_hertz == SAMPLE_RATE


async def test_get_medical_scribe_stream(
    healthscribe_resources: tuple[str, str],
) -> None:
    """Test non-streaming GetMedicalScribeStream operation.

    IAM is eventually consistent, so Transcribe may not be able to assume the
    newly created role immediately. Retry on BadRequestException until the
    role has propagated, or until the timeout is reached. Also retries on
    LimitExceededException (post-stream analytics job quota) and
    ThrottlingException (concurrent session limit) which can occur when
    multiple test runs execute in parallel.
    """
    role_arn, s3_bucket = healthscribe_resources

    last_error: BadRequestException | LimitExceededException | CallError | None = None
    try:
        async with asyncio.timeout(ROLE_PROPAGATION_TIMEOUT):
            while True:
                try:
                    await _run_medical_scribe_session(role_arn, s3_bucket)
                    return
                except (BadRequestException, LimitExceededException) as e:
                    # BadRequestException: IAM role not yet propagated.
                    # LimitExceededException: post-stream analytics job quota exceeded
                    last_error = e
                    await asyncio.sleep(ROLE_PROPAGATION_RETRY_DELAY)
                except CallError as e:
                    # ThrottlingException is not modeled in the error registry,
                    # so it surfaces as a generic CallError with
                    # is_throttling_error=False. Match by error id in message.
                    if "ThrottlingException" in str(e):
                        last_error = e
                        await asyncio.sleep(ROLE_PROPAGATION_RETRY_DELAY)
                    else:
                        raise
    except TimeoutError:
        assert last_error is not None
        raise last_error
