"""
Typed photo data models for the Flickr-to-Instagram automation pipeline.

Replaces raw dict-based photo data with explicit typed fields,
making the photo lifecycle stages clear and preventing missing-key bugs.
"""
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, List, Any


@dataclass
class PhotoListItem:
    """Lightweight photo from album listing (before enrichment).

    Returned by FlickrAPI.get_photo_list(). Contains only the fields
    available from the photoset listing endpoint (one API call for the whole album).
    """
    id: str
    title: str
    url: str
    server: str
    secret: str
    date_taken: str
    album_position: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EnrichedPhoto(PhotoListItem):
    """Fully enriched photo with metadata (after enrichment).

    Created by FlickrAPI.enrich_photo() which fetches per-photo info,
    location, and EXIF data via additional API calls.
    """
    description: str = ""
    photo_page_url: str = ""
    source_url: Optional[str] = None
    hashtags: str = ""
    exif_data: Optional[Dict[str, Any]] = None
    exif_hints: Optional[Dict[str, List[str]]] = field(default_factory=dict)
    location_data: Optional[Dict[str, Any]] = None
    selected_blog: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
