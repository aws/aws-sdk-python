# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test bidirectional event stream handling."""

import asyncio
import time
import uuid

from smithy_core.aio.eventstream import DuplexEventStream
from smithy_http.aio.crt import AWSCRTHTTPClient

from aws_sdk_connecthealth.models import (
    ClinicalNoteGenerationSettings,
    ClinicalNoteGenerationSettingsResponse,
    EncounterContext,
    GetMedicalScribeListeningSessionOutput,
    ManagedNoteTemplate,
    ManagedTemplate,
    MedicalScribeAudioEvent,
    MedicalScribeConfigurationEvent,
    MedicalScribeInputStream,
    MedicalScribeInputStreamAudioEvent,
    MedicalScribeInputStreamConfigurationEvent,
    MedicalScribeInputStreamSessionControlEvent,
    MedicalScribeLanguageCode,
    MedicalScribeMediaEncoding,
    MedicalScribeOutputStream,
    MedicalScribeOutputStreamTranscriptEvent,
    MedicalScribePostStreamActionSettings,
    MedicalScribePostStreamActionSettingsResponse,
    MedicalScribeSessionControlEvent,
    MedicalScribeSessionControlEventType,
    MedicalScribeStreamStatus,
    NoteTemplateSettingsManagedTemplate,
    NoteTemplateSettingsResponseManagedTemplate,
    StartMedicalScribeListeningSessionOutput,
)

from . import AUDIO_FILE, REGION, create_connecthealth_client, streaming_endpoint_plugin

SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2
CHANNEL_NUMS = 1
CHUNK_SIZE = 1024 * 8


async def _send_events(
    stream: DuplexEventStream[
        MedicalScribeInputStream,
        MedicalScribeOutputStream,
        StartMedicalScribeListeningSessionOutput,
    ],
    output_s3_uri: str,
) -> None:
    """Send configuration, audio chunks, and end-of-session control event."""
    await stream.input_stream.send(
        MedicalScribeInputStreamConfigurationEvent(
            value=MedicalScribeConfigurationEvent(
                post_stream_action_settings=MedicalScribePostStreamActionSettings(
                    output_s3_uri=output_s3_uri,
                    clinical_note_generation_settings=ClinicalNoteGenerationSettings(
                        note_template_settings=NoteTemplateSettingsManagedTemplate(
                            value=ManagedTemplate(
                                template_type=ManagedNoteTemplate.HISTORY_AND_PHYSICAL
                            )
                        )
                    ),
                ),
                encounter_context=EncounterContext(
                    unstructured_context=(
                        "Integration test encounter for SDK validation."
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


async def _receive_events(
    stream: DuplexEventStream[
        MedicalScribeInputStream,
        MedicalScribeOutputStream,
        StartMedicalScribeListeningSessionOutput,
    ],
    expected_session_id: str,
    expected_domain_id: str,
    expected_subscription_id: str,
) -> bool:
    """Receive and assert per-event-type fields.

    Returns:
        True if at least one transcript event with non-empty content was
        received.
    """
    got_transcript = False

    start_output, output_stream = await stream.await_output()

    assert isinstance(start_output, StartMedicalScribeListeningSessionOutput)
    assert start_output.session_id == expected_session_id
    assert start_output.domain_id == expected_domain_id
    assert start_output.subscription_id == expected_subscription_id
    assert start_output.request_id is not None
    assert start_output.language_code == MedicalScribeLanguageCode.EN_US
    assert start_output.media_encoding == MedicalScribeMediaEncoding.PCM
    assert start_output.media_sample_rate_hertz == SAMPLE_RATE

    if output_stream is None:
        return got_transcript

    async for event in output_stream:
        if isinstance(event, MedicalScribeOutputStreamTranscriptEvent):
            segment = event.value.transcript_segment
            assert segment is not None
            assert segment.segment_id is not None
            assert segment.audio_begin_offset is not None
            assert segment.audio_end_offset is not None
            assert segment.is_partial is not None
            assert segment.channel_id is not None
            if segment.content:
                got_transcript = True
        else:
            raise RuntimeError(
                f"Received unexpected event type in stream: {type(event).__name__}"
            )

    return got_transcript


async def test_start_medical_scribe_listening_session(connecthealth_resources) -> None:
    """Test bidirectional streaming with audio input and transcript output."""
    domain_id, subscription_id, output_s3_uri = connecthealth_resources

    async with await create_connecthealth_client(
        REGION, transport=AWSCRTHTTPClient()
    ) as client:
        endpoint_plugin = streaming_endpoint_plugin(REGION)
        session_id = str(uuid.uuid4())

        stream = await client.start_medical_scribe_listening_session(
            session_id=session_id,
            domain_id=domain_id,
            subscription_id=subscription_id,
            language_code=MedicalScribeLanguageCode.EN_US,
            media_sample_rate_hertz=SAMPLE_RATE,
            media_encoding=MedicalScribeMediaEncoding.PCM,
            plugins=[endpoint_plugin],
        )

        results = await asyncio.gather(
            _send_events(stream, output_s3_uri),
            _receive_events(stream, session_id, domain_id, subscription_id),
        )
        got_transcript = results[1]
        assert got_transcript, (
            "Expected to receive a transcript event with non-empty content"
        )

        response = await client.get_medical_scribe_listening_session(
            session_id=session_id,
            domain_id=domain_id,
            subscription_id=subscription_id,
            plugins=[endpoint_plugin],
        )
        assert isinstance(response, GetMedicalScribeListeningSessionOutput)
        details = response.medical_scribe_listening_session_details
        assert details is not None
        assert details.session_id == session_id
        assert details.stream_status == MedicalScribeStreamStatus.COMPLETED
        assert details.language_code == MedicalScribeLanguageCode.EN_US
        assert details.media_encoding == MedicalScribeMediaEncoding.PCM
        assert details.media_sample_rate_hertz == SAMPLE_RATE
        assert details.encounter_context_provided is True
        assert isinstance(
            details.post_stream_action_settings,
            MedicalScribePostStreamActionSettingsResponse,
        )
        assert details.post_stream_action_settings.output_s3_uri == output_s3_uri
        assert isinstance(
            details.post_stream_action_settings.clinical_note_generation_settings,
            ClinicalNoteGenerationSettingsResponse,
        )
        clinical_note_settings = (
            details.post_stream_action_settings.clinical_note_generation_settings
        )
        note_template = clinical_note_settings.note_template_settings
        assert isinstance(note_template, NoteTemplateSettingsResponseManagedTemplate)
        assert note_template.value is not None
        assert (
            note_template.value.template_type
            == ManagedNoteTemplate.HISTORY_AND_PHYSICAL
        )
        assert details.post_stream_action_result is not None
        assert details.stream_creation_time is not None
        assert details.stream_end_time is not None
