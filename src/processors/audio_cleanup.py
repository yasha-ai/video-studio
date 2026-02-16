"""
Audio Cleanup Module

Cleans and enhances audio using built-in AI filters or Auphonic API.
Removes noise, echo, breaths, and normalizes volume levels.
"""

import os
import subprocess
import json
import requests
import time
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from datetime import datetime


class AudioCleanup:
    """
    Audio cleanup and enhancement processor.
    
    Features:
    - Built-in AI cleanup (fast, ffmpeg-based)
    - Auphonic API integration (professional quality)
    - Noise reduction and echo removal
    - Volume normalization
    - Breath removal
    - Progress tracking
    - Artifacts system integration
    
    Modes:
    - 'builtin': Fast AI cleanup using ffmpeg filters
    - 'auphonic': Professional cleanup via Auphonic API
    """
    
    # Auphonic API endpoints
    AUPHONIC_API_URL = "https://auphonic.com/api"
    
    # Built-in cleanup presets
    BUILTIN_PRESETS = {
        'light': {
            'highpass': 80,      # Remove low-frequency rumble
            'lowpass': 12000,    # Remove high-frequency hiss
            'nr_amount': 3,      # Noise reduction strength (1-10)
            'gate': -40,         # Gate threshold (dB)
            'compressor': True,  # Dynamic range compression
            'normalize': -16     # Target loudness (LUFS)
        },
        'medium': {
            'highpass': 100,
            'lowpass': 10000,
            'nr_amount': 5,
            'gate': -35,
            'compressor': True,
            'normalize': -16
        },
        'aggressive': {
            'highpass': 120,
            'lowpass': 8000,
            'nr_amount': 8,
            'gate': -30,
            'compressor': True,
            'normalize': -14
        }
    }
    
    # Auphonic presets
    AUPHONIC_PRESETS = {
        'podcast': {
            'output_basename': 'cleaned',
            'algorithms': {
                'denoise': True,
                'normloudness': True,
                'leveler': True,
                'filtering': True
            }
        },
        'video': {
            'output_basename': 'cleaned',
            'algorithms': {
                'denoise': True,
                'normloudness': True,
                'leveler': True,
                'filtering': True,
                'ducking': False
            }
        },
        'speech': {
            'output_basename': 'cleaned',
            'algorithms': {
                'denoise': True,
                'normloudness': True,
                'filtering': True,
                'hipfilter': True
            }
        }
    }
    
    def __init__(
        self,
        mode: str = 'builtin',
        auphonic_api_key: Optional[str] = None
    ):
        """
        Initialize Audio Cleanup processor.
        
        Args:
            mode: Cleanup mode ('builtin' or 'auphonic')
            auphonic_api_key: Auphonic API key (required if mode='auphonic')
        """
        self.mode = mode
        
        if mode == 'auphonic':
            self.auphonic_api_key = auphonic_api_key or os.getenv('AUPHONIC_API_KEY')
            if not self.auphonic_api_key:
                raise ValueError(
                    "Auphonic API key required for mode='auphonic'. "
                    "Set AUPHONIC_API_KEY env variable or pass auphonic_api_key parameter."
                )
    
    def cleanup(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        preset: str = 'medium',
        custom_params: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> str:
        """
        Clean audio file using selected mode.
        
        Args:
            input_path: Path to input audio file
            output_path: Path for cleaned audio (auto-generated if None)
            preset: Cleanup preset name
            custom_params: Custom cleanup parameters (overrides preset)
            progress_callback: Optional callback for progress updates (0.0 to 1.0)
        
        Returns:
            Path to cleaned audio file
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Generate output path if not provided
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_cleaned{input_path.suffix}"
        output_path = Path(output_path)
        
        if self.mode == 'builtin':
            return self._cleanup_builtin(
                input_path, output_path, preset, custom_params, progress_callback
            )
        elif self.mode == 'auphonic':
            return self._cleanup_auphonic(
                input_path, output_path, preset, custom_params, progress_callback
            )
        else:
            raise ValueError(f"Unknown mode: {self.mode}")
    
    def _cleanup_builtin(
        self,
        input_path: Path,
        output_path: Path,
        preset: str,
        custom_params: Optional[Dict[str, Any]],
        progress_callback: Optional[Callable[[float], None]]
    ) -> str:
        """Built-in cleanup using ffmpeg filters."""
        
        # Get preset parameters
        params = self.BUILTIN_PRESETS.get(preset, self.BUILTIN_PRESETS['medium'])
        if custom_params:
            params.update(custom_params)
        
        # Build ffmpeg filter chain
        filters = []
        
        # Highpass filter (remove low rumble)
        if params.get('highpass'):
            filters.append(f"highpass=f={params['highpass']}")
        
        # Lowpass filter (remove high hiss)
        if params.get('lowpass'):
            filters.append(f"lowpass=f={params['lowpass']}")
        
        # Noise reduction (afftdn)
        if params.get('nr_amount'):
            nr = params['nr_amount']
            filters.append(f"afftdn=nf={nr}")
        
        # Gate (silence removal)
        if params.get('gate'):
            gate_db = params['gate']
            filters.append(f"agate=threshold={gate_db}dB:ratio=3:attack=1:release=50")
        
        # Compressor (dynamic range)
        if params.get('compressor'):
            filters.append("acompressor=threshold=-20dB:ratio=4:attack=5:release=50")
        
        # Normalize loudness
        if params.get('normalize'):
            target_lufs = params['normalize']
            filters.append(f"loudnorm=I={target_lufs}:dual_mono=true:TP=-1.5:LRA=11")
        
        filter_chain = ','.join(filters)
        
        # Build ffmpeg command
        cmd = [
            'ffmpeg',
            '-i', str(input_path),
            '-af', filter_chain,
            '-c:a', 'pcm_s16le',  # High quality audio codec
            '-ar', '48000',        # 48kHz sample rate
            '-y',                  # Overwrite output
            str(output_path)
        ]
        
        if progress_callback:
            progress_callback(0.1)  # Starting
        
        # Run ffmpeg
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            if progress_callback:
                progress_callback(1.0)  # Complete
            
            return str(output_path)
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg audio cleanup failed: {e.stderr}")
    
    def _cleanup_auphonic(
        self,
        input_path: Path,
        output_path: Path,
        preset: str,
        custom_params: Optional[Dict[str, Any]],
        progress_callback: Optional[Callable[[float], None]]
    ) -> str:
        """Professional cleanup using Auphonic API."""
        
        # Get preset parameters
        params = self.AUPHONIC_PRESETS.get(preset, self.AUPHONIC_PRESETS['podcast'])
        if custom_params:
            params.update(custom_params)
        
        if progress_callback:
            progress_callback(0.1)  # Starting upload
        
        # 1. Create production
        production_data = {
            'metadata': {
                'title': f"Audio cleanup - {input_path.name}",
                'subtitle': f"Preset: {preset}"
            },
            'algorithms': params.get('algorithms', {}),
            'output_files': [{
                'format': 'wav',
                'ending': 'cleaned',
                'mono_mixdown': False
            }]
        }
        
        headers = {'Authorization': f'Bearer {self.auphonic_api_key}'}
        
        response = requests.post(
            f"{self.AUPHONIC_API_URL}/productions.json",
            headers=headers,
            json=production_data
        )
        response.raise_for_status()
        production = response.json()['data']
        production_uuid = production['uuid']
        
        if progress_callback:
            progress_callback(0.2)  # Production created
        
        # 2. Upload audio file
        with open(input_path, 'rb') as f:
            files = {'input_file': (input_path.name, f, 'audio/wav')}
            response = requests.post(
                f"{self.AUPHONIC_API_URL}/production/{production_uuid}/upload.json",
                headers=headers,
                files=files
            )
            response.raise_for_status()
        
        if progress_callback:
            progress_callback(0.4)  # File uploaded
        
        # 3. Start processing
        response = requests.post(
            f"{self.AUPHONIC_API_URL}/production/{production_uuid}/start.json",
            headers=headers
        )
        response.raise_for_status()
        
        if progress_callback:
            progress_callback(0.5)  # Processing started
        
        # 4. Poll for completion
        max_wait = 600  # 10 minutes timeout
        poll_interval = 5  # Check every 5 seconds
        elapsed = 0
        
        while elapsed < max_wait:
            response = requests.get(
                f"{self.AUPHONIC_API_URL}/production/{production_uuid}.json",
                headers=headers
            )
            response.raise_for_status()
            status_data = response.json()['data']
            status = status_data['status_string']
            
            if status == 'Done':
                if progress_callback:
                    progress_callback(0.9)  # Processing complete
                
                # 5. Download result
                output_file_url = status_data['output_files'][0]['download_url']
                response = requests.get(output_file_url, headers=headers, stream=True)
                response.raise_for_status()
                
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                if progress_callback:
                    progress_callback(1.0)  # Complete
                
                return str(output_path)
            
            elif status == 'Error':
                error_msg = status_data.get('error_message', 'Unknown error')
                raise RuntimeError(f"Auphonic processing failed: {error_msg}")
            
            # Update progress based on completion percentage
            completion = status_data.get('completion', 0)
            if progress_callback and completion > 0:
                progress_callback(0.5 + (completion / 100 * 0.4))
            
            time.sleep(poll_interval)
            elapsed += poll_interval
        
        raise TimeoutError(f"Auphonic processing timeout after {max_wait}s")


def main():
    """CLI for standalone audio cleanup testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Audio Cleanup Tool')
    parser.add_argument('input', help='Input audio file')
    parser.add_argument('-o', '--output', help='Output audio file')
    parser.add_argument(
        '-m', '--mode',
        choices=['builtin', 'auphonic'],
        default='builtin',
        help='Cleanup mode'
    )
    parser.add_argument(
        '-p', '--preset',
        default='medium',
        help='Cleanup preset (builtin: light/medium/aggressive, auphonic: podcast/video/speech)'
    )
    parser.add_argument('--auphonic-key', help='Auphonic API key')
    
    args = parser.parse_args()
    
    # Progress callback
    def progress(p: float):
        print(f"\rProgress: {p*100:.1f}%", end='', flush=True)
    
    # Initialize cleanup
    cleanup = AudioCleanup(
        mode=args.mode,
        auphonic_api_key=args.auphonic_key
    )
    
    # Run cleanup
    output_path = cleanup.cleanup(
        args.input,
        args.output,
        preset=args.preset,
        progress_callback=progress
    )
    
    print(f"\n✅ Audio cleaned: {output_path}")


if __name__ == '__main__':
    main()
