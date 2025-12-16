"""
PulseAudio/PipeWire Helper Module

This module provides enhanced audio device enumeration by directly querying
PulseAudio/PipeWire instead of relying only on PyAudio's limited ALSA view.
This allows VoxInput to see all virtual devices like Easy Effects Source.
"""

import subprocess
import logging
import re

logger = logging.getLogger(__name__)


class PulseAudioDevice:
    """Represents a PulseAudio/PipeWire input source"""
    
    def __init__(self, name, description, index=None):
        self.name = name  # PulseAudio device name (e.g., easyeffects_source)
        self.description = description  # Human-readable description
        self.index = index  # Optional PyAudio index if available
        
    def __repr__(self):
        return f"PulseAudioDevice(name='{self.name}', description='{self.description}', index={self.index})"


def get_pulseaudio_sources():
    """
    Get list of all PulseAudio/PipeWire input sources.
    
    Returns:
        list of PulseAudioDevice objects
    """
    sources = []
    
    try:
        # Run pactl to get all sources
        result = subprocess.run(
            ['pactl', 'list', 'sources'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        
        # Parse the output
        current_source = {}
        for line in result.stdout.split('\n'):
            line = line.strip()
            
            # New source starts with "Source #"
            if line.startswith('Source #'):
                # Save previous source if it exists
                if current_source and 'name' in current_source:
                    sources.append(PulseAudioDevice(
                        name=current_source['name'],
                        description=current_source.get('description', current_source['name'])
                    ))
                current_source = {}
            
            # Extract name
            elif line.startswith('Name:'):
                name = line.split('Name:', 1)[1].strip()
                current_source['name'] = name
            
            # Extract description
            elif line.startswith('Description:'):
                desc = line.split('Description:', 1)[1].strip()
                current_source['description'] = desc
        
        # Don't forget the last source
        if current_source and 'name' in current_source:
            sources.append(PulseAudioDevice(
                name=current_source['name'],
                description=current_source.get('description', current_source['name'])
            ))
        
        logger.info(f"Found {len(sources)} PulseAudio sources")
        
    except subprocess.TimeoutExpired:
        logger.error("Timeout while querying PulseAudio sources")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to query PulseAudio sources: {e}")
    except Exception as e:
        logger.error(f"Unexpected error querying PulseAudio sources: {e}")
    
    return sources


def filter_input_sources(sources):
    """
    Filter out non-microphone sources (monitors, outputs, etc.)
    
    Args:
        sources: list of PulseAudioDevice objects
        
    Returns:
        Filtered list of PulseAudioDevice objects suitable for microphone input
    """
    filtered = []
    
    # Keywords that indicate this is NOT a real microphone input
    exclude_keywords = [
        '.monitor',  # Monitor devices (outputs being monitored)
    ]
    
    # Additional descriptions to exclude
    exclude_descriptions = [
        'monitor of',  # Case-insensitive check
    ]
    
    for source in sources:
        # Check name for exclusions
        if any(keyword in source.name.lower() for keyword in exclude_keywords):
            logger.debug(f"Excluding source (name): {source.name}")
            continue
        
        # Check description for exclusions
        desc_lower = source.description.lower()
        if any(keyword in desc_lower for keyword in exclude_descriptions):
            logger.debug(f"Excluding source (description): {source.description}")
            continue
        
        filtered.append(source)
    
    logger.info(f"Filtered to {len(filtered)} input sources")
    return filtered


def set_default_source(source_name):
    """
    Set the default PulseAudio input source.
    
    Args:
        source_name: PulseAudio device name (e.g., 'easyeffects_source')
        
    Returns:
        True if successful, False otherwise
    """
    try:
        subprocess.run(
            ['pactl', 'set-default-source', source_name],
            check=True,
            timeout=5
        )
        logger.info(f"Set default source to: {source_name}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to set default source: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error setting default source: {e}")
        return False


def get_default_source():
    """
    Get the current default PulseAudio input source name.
    
    Returns:
        Source name string, or None if unable to determine
    """
    try:
        result = subprocess.run(
            ['pactl', 'get-default-source'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        source_name = result.stdout.strip()
        logger.info(f"Current default source: {source_name}")
        return source_name
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get default source: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting default source: {e}")
        return None


if __name__ == "__main__":
    # Test the module
    logging.basicConfig(level=logging.DEBUG)
    
    print("All PulseAudio Sources:")
    print("=" * 80)
    sources = get_pulseaudio_sources()
    for s in sources:
        print(f"  {s.name}")
        print(f"    → {s.description}")
    
    print("\nFiltered Input Sources:")
    print("=" * 80)
    inputs = filter_input_sources(sources)
    for s in inputs:
        print(f"  {s.name}")
        print(f"    → {s.description}")
    
    print("\nCurrent Default Source:")
    print("=" * 80)
    default = get_default_source()
    print(f"  {default}")
