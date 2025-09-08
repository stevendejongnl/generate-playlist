import json
import os
import logging
from typing import List

from flask import request, jsonify

logger = logging.getLogger(__name__)


class BlacklistManager:
    data_dir: str
    filepath: str

    def __init__(self, data_dir: str = 'data', filename: str = 'blacklist.json') -> None:
        self.data_dir = data_dir
        self.filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            logger.info(f"Created data directory: {self.data_dir}")
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w') as f:
                json.dump({'tracks': []}, f)
            logger.info(f"Created blacklist file: {self.filepath}")

    def get_tracks(self) -> List[str]:
        logger.info(f"Reading tracks from blacklist: {self.filepath}")
        with open(self.filepath) as f:
            data = json.load(f)
        logger.debug(f"Blacklist tracks: {data.get('tracks', [])}")
        return data.get('tracks', [])

    def add_track(self, track: str) -> List[str]:
        track = track.strip()
        if not track:
            logger.warning("Attempted to add empty track to blacklist.")
            return self.get_tracks()
        with open(self.filepath, 'r+') as f:
            data = json.load(f)
            tracks = data.get('tracks', [])
            if track not in tracks:
                tracks.append(track)
                data['tracks'] = tracks
                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()
                logger.info(f"Added track to blacklist: {track}")
            else:
                logger.info(f"Track already in blacklist: {track}")
        return tracks

    def delete_track(self, track: str) -> List[str]:
        logger.info(f"Deleting track from blacklist: {track}")
        with open(self.filepath, 'r+') as f:
            data = json.load(f)
            tracks = data.get('tracks', [])
            tracks = [t for t in tracks if t != track]
            data['tracks'] = tracks
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
        logger.info(f"Track deleted from blacklist: {track}")
        return tracks

    def add_tracks(self, tracks: List[str]) -> List[str]:
        clean_tracks = [t.strip() for t in tracks if t.strip()]
        logger.info(f"Adding multiple tracks to blacklist: {clean_tracks}")
        with open(self.filepath, 'r+') as f:
            data = json.load(f)
            current_tracks = set(data.get('tracks', []))
            current_tracks.update(clean_tracks)
            data['tracks'] = list(current_tracks)
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
        logger.info(f"Updated blacklist with new tracks.")
        return data['tracks']
