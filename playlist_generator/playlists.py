import json
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def extract_playlist_id(value: str) -> str:
    """Extract a Spotify playlist ID from a URL or return the raw ID."""
    value = value.strip()
    if 'spotify.com/playlist/' in value:
        return value.split('spotify.com/playlist/')[1].split('?')[0].split('/')[0]
    return value


class PlaylistManager:
    data_dir: str
    filepath: str

    def __init__(self, data_dir: str = 'data', filename: str = 'playlists.json') -> None:
        self.data_dir = data_dir
        self.filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            logger.info(f"Created data directory: {self.data_dir}")
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w') as f:
                json.dump(self._default_data(), f)
            logger.info(f"Created playlists file: {self.filepath}")

    def _default_data(self) -> Dict[str, Any]:
        return {"target": "", "sources": []}

    def get_data(self) -> Dict[str, Any]:
        with open(self.filepath) as f:
            data = json.load(f)
        return data

    def get_target(self) -> str:
        return self.get_data().get("target", "")

    def get_sources(self) -> List[Dict[str, str]]:
        return self.get_data().get("sources", [])

    def add_source(self, playlist_id: str, name: str) -> Dict[str, Any]:
        playlist_id = playlist_id.strip()
        name = name.strip() or playlist_id
        with open(self.filepath, 'r+') as f:
            data = json.load(f)
            sources = data.get("sources", [])
            if not any(s["id"] == playlist_id for s in sources):
                sources.append({"id": playlist_id, "name": name})
                data["sources"] = sources
                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()
                logger.info(f"Added source playlist: {playlist_id} ({name})")
            else:
                logger.info(f"Source playlist already exists: {playlist_id}")
        return data

    def delete_source(self, playlist_id: str) -> Dict[str, Any]:
        with open(self.filepath, 'r+') as f:
            data = json.load(f)
            data["sources"] = [s for s in data.get("sources", []) if s["id"] != playlist_id]
            if data.get("target") == playlist_id:
                data["target"] = ""
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
        logger.info(f"Deleted source playlist: {playlist_id}")
        return data

    def set_target(self, playlist_id: str) -> Dict[str, Any]:
        with open(self.filepath, 'r+') as f:
            data = json.load(f)
            data["target"] = playlist_id
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
        logger.info(f"Set target playlist: {playlist_id}")
        return data
