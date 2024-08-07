import os

from datetime import (
    datetime,
    timedelta,
    UTC as utc_tz,
)

from gong.calls import (
    GongCallBaseFilter,
    GongCallContentSelector,
    GongCallDetailsRequest,
    GongCallExposedFields,
    GongCallTranscriptFilter,
)
from gong.client import GongClient

GONG_SUBDOMAIN = ''


BASE_URL = f'https://{GONG_SUBDOMAIN}.api.gong.io/'


def initialize_client(access_key: str = None, secret_access_key: str = None, url: str = BASE_URL) -> GongClient:
    """
    Create a Gong client

    Will use the environment variables GONG_ACCESS_KEY and GONG_SECRET_ACCESS_KEY if credentials
    are not provided

    Keyword Arguments:
    access_key -- Gong access key
    secret_access_key -- Gong secret access key
    url -- Gong API base url
    """
    gong_access_key =  os.environ.get('GONG_ACCESS_KEY', access_key)

    gong_secret_access_key = os.environ.get('GONG_SECRET_ACCESS_KEY', secret_access_key)

    missing_keys = []

    if not gong_access_key:
        missing_keys.append('Access Key')

    if not gong_secret_access_key:
        missing_keys.append('Secret Access Key')
        
    if missing_keys: 
        raise ValueError(
            'Access Key and Secret Access Key must not be empty:\nMissing {}'.format(', '.join(missing_keys))
        )

    return GongClient(
        access_key=gong_access_key,
        access_key_secret=gong_secret_access_key,
        base_url=url
    )


def list_calls_for_week(access_key: str = None, secret_access_key: str = None,
                        start_date: datetime = None, url: str = BaseUrl):
    """
    Retrieve calls for the week

    Keyword Arguments:
    access_key -- Gong access key
    secret_access_key -- Gong secret access key
    start_date -- Start date for the week
    url -- Gong API base url
    """

    client = initialize_client()

    # Get the current date
    if not start_date:
        current_date = datetime.now(tz=utc_tz)

    else:
        current_date = start_date

    # Get the start of the week
    start_of_week = current_date - timedelta(days=7)

    filter = GongCallBaseFilter(
        from_date_time=start_of_week,
        to_date_time=current_date,
    )

    return client.calls(filter=filter)


def get_transcript(call_id: str, call_title: str, call_start_time: datetime, url: str) -> str:
    """
    Retrieve the transcript for a call. A transcript is returned with speaker information.

    Keyword Arguments:
    call_id -- The call id
    call_title -- The title of the call
    call_start_time -- The start time of the call
    url -- Gong call url
    """
    client = initialize_client()

    base_filter = GongCallBaseFilter(call_ids=[call_id])

    call_detail_req = GongCallDetailsRequest(
        filter=base_filter,
        content_selector=GongCallContentSelector(
            exposed_fields=GongCallExposedFields(
                parties=True
            )
        )
    )

    call_details = client.call_details(call_detail_req)

    speakers = {}

    speaker_info = []

    for call in call_details.response_obj.calls:
        parties = call.parties

        for party in parties:
            if not party.speaker_id:
                continue

            speakers[party.speaker_id] = party.name

            speaker_name_plate = party.name

            if party.title:
                speaker_name_plate += f' ({party.title})'

            if party.affiliation == 'Internal':
                speaker_name_plate += ' - Caylent'

            elif party.email_address and 'amazon.com' in party.email_address:
                speaker_name_plate += ' - Amazon'

            speaker_info.append(speaker_name_plate)
    
    try:
        returned_transcripts = client.call_transcripts(GongCallTranscriptFilter(filter=base_filter))

    except TypeError:
        raise ValueError('No transcripts found for the call')

    transcript_interactions = []

    transcript = returned_transcripts.response_obj.call_transcripts[0]

    monologues = transcript.transcript

    for monologue in monologues:
        monologue_speaker = monologue.speaker_id

        sentences = [sent.text for sent in monologue.sentences]

        full_text = '\n'.join(sentences)

        speaker_name = speakers[monologue_speaker]

        transcript_interactions.append(f'{speaker_name}:\n{full_text}')

    final_transcript = f'Title: {call_title}\n\nCall Start Time: {call_start_time}\n\n'

    final_transcript += f'Call URL: {url}\n\n'

    final_transcript += 'Participants in the call:\n\n' + '\n'.join(speaker_info) + '\n\n'

    final_transcript += '\n\n'.join(transcript_interactions)

    return final_transcript
