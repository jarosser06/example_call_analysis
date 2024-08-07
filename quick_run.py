'''Kicks off a quick Test Analysis run for the last week worth of calls'''

import json

from os.path import exists as path_exists
from os import mkdir

from call_analysis.analysis import Analyzer
from call_analysis.calls import list_calls_for_week, get_transcript

call_list = list_calls_for_week()

resp_obj = call_list.response_obj

calls = resp_obj.calls

analyzer = Analyzer()

if not path_exists('calls'):
    mkdir('calls')

    for sub_dir in ['analysis', 'processed']:
        mkdir(f'calls/{sub_dir}')

for call in calls:
    print(f'Processing call: {call.id}')

    processed_file_path = f'calls/processed/{call.id}'

    if path_exists(processed_file_path):
        print(f'Analysis already exists for call: {call.id}')

        continue

    try:
        call_transcript = get_transcript(call.id, call.title, call.started, call.url)

    except ValueError:
        print(f'No transcript found for call: {call.id}')

        with open(processed_file_path, 'w+') as processed_file:
            processed_file.write('')

        continue

    analysis = analyzer.analyze(call_transcript)

    transcript_file = open(f'calls/analysis/{call.id}-transcript.txt', 'w+')

    transcript_file.write(call_transcript)

    transcript_file.close()

    analysis_file = open(f'calls/analysis/{call.id}-analysis.json', 'w+')

    analysis_file.write(json.dumps(analysis, indent=4))

    analysis_file.close()

    with open(processed_file_path, 'w+') as processed_file:
        processed_file.write('')

    print(f'Transcript saved for call: {call.id}')
