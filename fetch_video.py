from aiohttp import ClientSession
import re
import urllib.parse
import json

from util import get_default_headers, index_s, int_s

async def fetch_video(videoId: str, chunk_size: int = 1024):
    """
    Fetch all metadata of a YouTube video.

    Performs one asynchronous HTTP request to obtain all metadata.

    Result:
    {
        'id': string,
        'title': string,
        'shortDescription': string,
        'thumbnails': [
            {
                '',
            }
        ],
        'length': integer,
        'views': integer,
        'uploader': {
            'name': string,
            'url': string
        },
        'items' [
            {
                'id': string,
                'title': string,
                'uploader': {
                    'name': string,
                    'url': string
                }
                'lengthSeconds': integer,
            }
        ]
    }
    """

    #
    # Initialize the result.
    #

    video = {'id': videoId}

    #
    # Build the headers for the ClientSession.
    #

    headers = get_default_headers()
    # Only accept the urlencoded response.
    headers['Accept'] = 'application/x-www-form-urlencoded'

    #
    # Retrieve info.
    #

    async with ClientSession(headers=headers, raise_for_status=True) as session:
        async with session.get('https://www.youtube.com/get_video_info?video_id=' + videoId) as response:
            # Assert that this really worked the way we wanted.
            assert response.status == 200
            assert response.content_type == 'application/x-www-form-urlencoded'

            # Parse the video info (large!).
            # TODO: This ought to be streamed.
            info = urllib.parse.parse_qs(await response.text())
            info = json.loads(info['player_response'][0])

            #
            # Copy relevant data.
            #

            # Details.
            details = index_s(info, 'videoDetails')
            video['title'] = index_s(details, 'title')
            video['lengthSeconds'] = int_s(index_s(details, 'lengthSeconds'))
            video['keywords'] = list(index_s(details, 'keywords', default=[]))
            video['shortDescription'] = index_s(details, 'shortDescription')
            video['thumbnails'] = list(index_s(details, 'thumbnail', 'thumbnails', default=[]))
            video['views'] = int_s(index_s(details, 'viewCount'))
            video['uploader'] = {
                'name': index_s(details, 'author'),
                'channelId': index_s(details, 'channelId'),
                # TODO: Derive from channel ID?
                'url': None,
            }

            # Caption tracks.
            video['captionTracks'] = list(index_s(info, 'captions', 'playerCaptionsTracklistRenderer', 'captionTracks', default=[]))

    return video

#
# Command line tool.
#

if __name__ == '__main__':
    from argparse import ArgumentParser, FileType
    import sys
    from io import TextIOWrapper
    from tqdm import tqdm
    import json

    from util import run_sync

    #
    # Command line interface.
    #

    cli = ArgumentParser(description='Fetch YoutTube video metadata')
    cli.add_argument(
        'videoId',
        metavar='ID',
        nargs='+',
        help='video id'
    )
    cli.add_argument(
        '--output',
        nargs='?',
        default='video_{id}.json',
        help='file name for output'
    )
    cli.add_argument(
        '--pretty',
        action='store_true',
        default=False,
        help='prettify JSON output'
    )
    cli.add_argument(
        '--chunk-size',
        dest='chunk_size',
        type=int,
        default=1024,
        help='streaming chunk size'
    )
    args = cli.parse_args()

    def open_output(id: str):
        if args.output == '-':
            return TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

        path = args.output.format(id=id)
        return open(path, 'w', encoding='utf8')

    dump = lambda x,f: json.dump(x, f)
    if args.pretty:
        dump = lambda x,f: json.dump(x, f, indent=4, separators=(',',': '))

    try:
        for id in tqdm(args.videoId, file=sys.stderr):
            with open_output(id) as file:
                try:
                    dump(run_sync(fetch_video, id, args.chunk_size), file)
                except Exception as e:
                    print("\nError fetching video:", file=sys.stderr)
                    print(e, file=sys.stderr)

        sys.exit(0)
    except Exception as e:
        print("\nUnexpected error:", file=sys.stderr)
        print(e, file=sys.stderr)
        sys.exit(1)