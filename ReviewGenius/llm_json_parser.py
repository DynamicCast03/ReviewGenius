import json
from typing import Generator, Dict, Any

def stream_json_with_events(text_stream: Generator[str, None, None]) -> Generator[Dict[str, Any], None, None]:
    """
    Receives a text stream, parses JSON objects from it, and generates events during parsing.
    - 'start': Fired when the start of a JSON object ('{') is detected.
    - 'streaming': Transmits raw text chunks as they arrive.
    - 'end': Fired when a complete JSON object has been successfully parsed, containing the parsed data.
    - 'error': Fired when a JSON parsing error occurs.

    :param text_stream: A generator that continuously produces text chunks.
    :return: A generator that produces event dictionaries one by one.
    """
    buffer = ""
    json_started = False
    
    while True:
        try:
            # Read from the stream until we have something to process
            chunk = next(text_stream)
            print(chunk, end="") # Server-side debug print
            buffer += chunk
        except StopIteration:
            # Stream ended
            break

        if not json_started:
            try:
                start_index = buffer.index('{')
                json_started = True
                yield {'type': 'start'}
                
                # Yield the content from the brace onwards as the first streaming chunk
                content_chunk = buffer[start_index:]
                yield {'type': 'streaming', 'content': content_chunk}

                # The buffer for our JSON object starts from the first brace
                buffer = content_chunk
            except ValueError:
                # Still waiting for '{', clear buffer if it gets too large to avoid memory issues
                if len(buffer) > 1024:
                    buffer = ""
                continue
        else:
            # Already in a JSON object, the whole chunk is content
            yield {'type': 'streaming', 'content': chunk}

        # Attempt to find and parse a complete JSON object in the buffer
        if json_started:
            brace_counter = 0
            end_index = -1
            for i, char in enumerate(buffer):
                if char == '{':
                    brace_counter += 1
                elif char == '}':
                    brace_counter -= 1
                    if brace_counter == 0:
                        end_index = i
                        break
            
            if end_index != -1:
                potential_json_str = buffer[:end_index + 1]
                try:
                    parsed_json = json.loads(potential_json_str)
                    yield {'type': 'end', 'data': parsed_json}
                    
                    # Reset for the next object
                    buffer = buffer[end_index + 1:]
                    json_started = False
                except json.JSONDecodeError as e:
                    # It looked like a full object, but wasn't. This is an error case.
                    # We should probably discard this attempt and restart.
                    yield {'type': 'error', 'message': f"JSON Decode Error for: {potential_json_str[:100]}..."}
                    # Discard the invalid part and reset
                    buffer = buffer[end_index + 1:]
                    json_started = False

    # After stream ends, there might be leftover buffer content. We can try to parse it.
    # This part is complex and might not be needed if the stream is guaranteed to finish with a complete JSON.
    # For now, we'll ignore leftovers.
