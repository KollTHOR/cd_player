"""
CD Metadata Lookup via MusicBrainz (using python-discid)

- Uses python-discid to extract the real MusicBrainz disc ID from the CD drive.
- Fetches album and track titles from MusicBrainz using the disc ID.
- Falls back to generic titles if lookup fails.
- Provides detailed logging for debugging.
"""

import sys
import pprint

# Ensure user site-packages are in path (optional, for user installs)
sys.path.insert(0, "/home/orangepi/.local/lib/python3.12/site-packages")

import musicbrainzngs
import discid

def get_discid(device='/dev/sr0'):
    """Get the MusicBrainz disc ID and available disc info."""
    try:
        print(f"🔍 Reading discid from {device} ...")
        disc = discid.read(device)
        print(f"✅ Disc ID: {disc.id}")
        # Print available attributes
        if hasattr(disc, 'sectors'):
            print(f"   Sectors: {disc.sectors}")
        if hasattr(disc, 'tracks'):
            print(f"   Tracks: {disc.tracks}")
        return disc
    except Exception as e:
        print(f"❌ Error reading discid: {e}")
        return None

def get_musicbrainz_metadata_by_discid(disc):
    """
    Query MusicBrainz for CD metadata using the disc ID.
    Returns (album_title, artist, [track_titles]) or None on failure.
    """
    try:
        musicbrainzngs.set_useragent("CDPlayer", "1.0", "youremail@example.com")
        print(f"🔍 Querying MusicBrainz for discid: {disc.id}")
        result = musicbrainzngs.get_releases_by_discid(disc.id, includes=["recordings"])
        print("📋 MusicBrainz get_releases_by_discid() result:")
        pprint.pprint(result)
        # Pick the first release
        release = result['disc']['release-list'][0]
        album_title = release.get('title', 'Unknown Album')
        # Robust artist extraction
        artist = (
            release.get('artist-credit', [{}])[0]
            .get('artist', {})
            .get('name', "Unknown Artist")
        )
        # Track titles
        medium = release['medium-list'][0]
        track_list = medium['track-list']
        track_titles = [track['recording']['title'] for track in track_list]
        print(f"✅ Album: {album_title}")
        print(f"✅ Artist: {artist}")
        print(f"✅ Track titles: {track_titles}")
        return album_title, artist, track_titles
    except Exception as e:
        print(f"❌ MusicBrainz lookup failed: {e}")
        return None

def get_cd_metadata(device='/dev/sr0'):
    """
    Main entry: returns (album_title, artist, [track_titles])
    Falls back to generic track names if lookup fails.
    """
    disc = get_discid(device)
    if disc:
        metadata = get_musicbrainz_metadata_by_discid(disc)
        if metadata:
            return metadata
        else:
            print("⚠️ No metadata found, using generic track names.")
            total = disc.last_track_num
            return ("Unknown Album", "Unknown Artist", [f"Track {i:02d}/{total:02d}" for i in range(1, total+1)])
    else:
        print("⚠️ Could not read disc ID, using generic track names.")
        total = 8
        return ("Unknown Album", "Unknown Artist", [f"Track {i:02d}/{total:02d}" for i in range(1, total+1)])

if __name__ == "__main__":
    album, artist, tracks = get_cd_metadata()
    print(f"\nAlbum: {album}\nArtist: {artist}")
    for i, title in enumerate(tracks, 1):
        print(f"{i:02d}: {title}")
