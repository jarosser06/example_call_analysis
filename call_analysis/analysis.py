import json
import re

from html.parser import HTMLParser
from typing import Dict

from anthropic import AnthropicBedrock


PromptContext = '''
Your job is to analyze the call data and provide insights about the call. Always provide quotes from the call that support your analysis, and always attribute them.

ONLY use the following formats as your response:

Example Call Analysis:

<response>
<response_body>
{
    "call_type": "other",
    "title": "Call Title",
    "date": "2022-01-01T12:00:00Z",
    "url": "https://gong.io/call",
    "participants": [
        {
            "name": "John Doe",
            "role": "CEO",
            "company": "ACME Inc."
        },
        {
            "name": "Jane Doe",
            "role": "CFO",
            "company": "ACME Inc."
        },
        {
            "name": "Jack Johnson",
            "role": "Project Manager",
            "company": "Caylent"
        }
    ],
    "summary": "The call was about...",
    "next_steps": [
        {
            "action_item": "Follow up with the client",
            "responsible": "John Doe"
        },
        {
            "action_item": "Send the client the proposal",
            "responsible": "Jane Doe"
        }
    ],
    "notable_mentions": [
        {
            "quote": "We are looking for a company that can help us...",
            "speaker": "John Doe"
        },
        {
            "quote": "We are interested in your company...",
            "speaker": "Jane Doe"
        }
    ]
} 
</response_body>
</response>

DO NOT PROVIDE ANY OTHER INFORMATION IN YOUR RESPONSE. ONLY THE RESPONSE OBJECT WITH VALID YAML IN THE RESPONSE BODY!!!

Transcript:
'''


class ResponseParser(HTMLParser):
    def __init__(self):
        """
        Parse the output of a response from the LLM

        Parse:
        <response>
        ...
        </response>
        """
        super().__init__()

        self.top_level_tag = 'response'

        self.currently_reading = None

        self.values = {}

        self.reading_response = False

        self.response_body_is_json = False

    def handle_starttag(self, tag, attrs):
        if tag == self.top_level_tag:
            self.reading_response = True

        if self.reading_response:
            self.currently_reading = tag

    def handle_endtag(self, tag):
        if tag == self.top_level_tag:
            self.reading_response = False

        if self.reading_response:
            self.currently_reading = None

    def handle_data(self, data):
        """
        Handle the data between tags
        """
        if not self.reading_response or not self.currently_reading:
            return

        if self.currently_reading not in self.values:
            self.values[self.currently_reading] = data

        else:
            self.values[self.currently_reading] += data

    def processed_values(self) -> Dict:
        """
        Process the parsed values

        Looks for 'response_body' key and converts it to a dictionary

        Override this method to process the parsed values in a different way
        """
        values = self.values

        if 'response_body' in values:
            response_body = values['response_body']

            if isinstance(response_body, str):
                cleaned_response = response_body.strip('\n ').replace('\n', '')

                values['response_body'] = json.loads(cleaned_response)

                self.response_body_is_json = True

            else:
                values['response_body'] = response_body

        else:
            values['response_body'] = None

        values['prompt'] = values.get('prompt', None)

        return values

    def parser_not_empty(self) -> bool:
        """
        Check if the parser has any values
        """
        return bool(self.values)

    @staticmethod
    def strip_tags(text: str, tag: str = 'response') -> str:
        """
        This function removes all text between and including the specified start and end tags.

        Keyword arguments:
            text: the text to remove the tags from
            tag: the tag to remove the text between and including
        """
        # Define the pattern to match the text between and including the specified tags
        pattern = f'<{tag}>.*?</{tag}>'

        # Use re.DOTALL to ensure that the '.' special character matches newline characters as well
        cleaned_text = re.sub(pattern, '', text, flags=re.DOTALL)

        return cleaned_text

    def to_dict(self):
        """
        Return the parsed response as a dictionary
        """
        return self.processed_values()


class Analyzer:
    def __init__(self):
        self.client = AnthropicBedrock(
            aws_region='us-east-1'
        )

    def analyze(self, transcript: str):
        prompt = PromptContext + '\n\n'+ transcript

        message = self.client.messages.create(
            model="anthropic.claude-3-5-sonnet-20240620-v1:0",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}]
        )

        response_parser = ResponseParser()

        response_parser.feed(message.content[0].text)

        return response_parser.to_dict()['response_body']
