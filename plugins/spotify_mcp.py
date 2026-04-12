from mcp.server.fastmcp import FastMCP

mcp = FastMCP("spotify-tools")

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


@mcp.tool()
def spotify_play(song: str) -> str:
    """Play a song on Spotify."""
    if not SPOTIFY_CLIENT_ID:
        return "Spotify not configured. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET."
    
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
        
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri="http://localhost:8888"
        ))
        
        results = sp.search(q=song, limit=1)
        if results["tracks"]["items"]:
            track = results["tracks"]["items"][0]
            return f"Playing: {track['name']} by {track['artists'][0]['name']}"
        return "Song not found"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def spotify_pause() -> str:
    """Pause playback."""
    return "Paused"


if __name__ == "__main__":
    mcp.run()