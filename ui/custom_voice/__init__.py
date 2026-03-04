import os
import streamlit.components.v1 as components

_RELEASE = True

if not _RELEASE:
    _component_func = components.declare_component(
        "custom_voice_input",
        url="http://localhost:3001",
    )
else:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "frontend")
    _component_func = components.declare_component("custom_voice_input", path=build_dir)

def voice_input(key=None, audio_b64=None, resume_listening=False, conv_mode_active=False, audio_id="", pending_upload=False, video_processing=False, clear_input=False):
    """
    Shows a chat input bar with conversation mode mic button and upload (+) button.

    Args:
        key: Streamlit component key.
        audio_b64: Base64-encoded audio to send back to the component for playback.
        resume_listening: If True, tells the component to resume listening after processing.
        conv_mode_active: If True, tells the component to restore conversation mode after rerun.
        audio_id: Unique ID for the audio to prevent replaying the same audio.
        pending_upload: If True, indicates a file is currently being processed.
        video_processing: If True, indicates a video is currently being processed.
        clear_input: If True, tells the component to clear the input text.

    Returns a dict with 'text', 'ts' (timestamp), 'convMode' (bool), and optionally 'action'.
    """
    return _component_func(
        key=key,
        audio_b64=audio_b64 or "",
        resume_listening=resume_listening,
        conv_mode_active=conv_mode_active,
        audio_id=audio_id or "",
        pending_upload=pending_upload,
        video_processing=video_processing,
        clear_input=clear_input,
        default=None,
    )
