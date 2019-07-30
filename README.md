# YT-INDEX

Utility for indexing YouTube videos.

## Goals

* Provide a toolset for creating search indices out of YouTube videos.
  * Does not include downloading of video/audio and other multimedia related problems!
* Provide alternatives to YouTube API calls.
  * Currently a seperate project.
* Allow both CLI and Python module usage.

## Components

### `fetch_playlist`

Fetch YouTube playlist metadata.

Crawls the `https://www.youtube.com/playlist?list={playlistId}` page for
information, performing the AJAX continuation loads.

Could be completely replaced by YouTube API calls to obtain more information.

All information is obtained at-once, and though the subsequent requests are
triggered asynchronously, large chunks of data still need to be read into
memory. All results are returned at once.

```json
{
    "id": string,           // playlistId
    "title": string,        // UTF-8 simple title
    "description": string,  // UTF-8 description
    "thumbnail": string,    // URL to default-sized playlist thumbnail
    "length": integer,      // number of videos
    "views": integer,       // number of views
    "uploader": {
        "name": string,     // UTF-8 simple name
        "url": string       // URL to user
    },
    "items": [
        {
            "id": string,               // videoId
            "title": string,            // UTF-8 simple title
            "uploader": {
                "name": string,         // UTF-8 simple name
                "url": string           // URL to user
            },
            "lengthSeconds": integer,   // length in seconds
        }
    ]
}
```

#### TODO

* Streaming continuation contents.

### `fetch_video`

Fetch YouTube video metadata.

Parses the `http://www.youtube.com/get_video_info?videoId={videoId}` response
for information.

Discards most of the repsonse. Could not entirely be replaced by YouTube API
calls because of security restrictions.

Large chunks of data need to be read into memory.

```json
{
    "id": string,               // videoId
    "title": string,            // UTF-8 simple title
    "lengthSeconds": integer,   // length in seconds
    "keywords": [ string ],     // keywords
    "shortDescription": string, // UTF-8 short description
    "thumbnails": [
        {
            "url": string,      // URL of image
            "width": integer,   // width in pixels
            "height": integer   // height in pixels
        }
    ],
    "views": integer,           // number of views
    "uploader": {
        "name": string,         // UTF-8 simple name
        "channelId": string,    // channelId
        "url": null             // NOT OBTAINABLE FROM HERE
    },
    "captionTracks": [
        {
            "url": string,          // URL to the TTML
            "name": string,         // UTF-8 localized track name
            "languageCode": string, // caption language code
            "kind": string          // caption kind (asr, ...)
        }
    ]
}
```

#### TODO

* Streaming.