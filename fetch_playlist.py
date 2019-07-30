"""Fetch playlist metadata from YouTube."""

from aiohttp import ClientSession
from lxml import etree
import re

from util import get_default_headers, has_brotli, index_s, is_valid_encoding, parse_int, parse_ts

async def fetch_playlist(playlistId: str, chunk_size: int = 1024):
    """
    Fetch all metadata of a YouTube playlist.

    Performs multiple asynchronous HTTP requests to obtain all metadata and
    playlist items. Does not provide rich YouTube metadata: fields that are
    included in browse_request queries for modern JS YT-Clients.

    Result:
    {
        'id': string,
        'title': string,
        'description': string,
        'thumbnail': string,
        'length': integer,
        'views': integer,
        'uploader': {
            'name': string,
            'url': string
        },
        'items': [
            {
                'id': string,
                'title': string,
                'uploader': {
                    'name': string,
                    'url': string
                },
                'lengthSeconds': integer,
            }
        ]
    }
    """

    #
    # Initialize the result
    #

    playlist = {
        'id': playlistId,
        'items': []
    }

    #
    # Build the headers for the ClientSession.
    #

    headers = get_default_headers()
    # Only accept HTML.
    headers['Accept'] = 'text/html'

    #
    # Retrieve landing page.
    #

    # Open a auto-raising ClientSession with default cookie handling.
    async with ClientSession(headers=headers, raise_for_status=True) as session:
        # Step 1: Get the initial landing page.
        async with session.get(
            'https://www.youtube.com/playlist',
            params={'list': playlistId}
        ) as response:
            # Assert that this really worked the way we wanted.
            assert response.status == 200
            assert response.content_type == 'text/html'
            encoding = response.get_encoding()
            assert is_valid_encoding(encoding)

            # Retrieve the '//div[@id=""]' node.
            is_content = lambda x: (x.tag, x.get('id')) == ('div', '')
            parser = etree.HTMLPullParser(events=('start', 'end'))
            content, discard = None, True
            while content is None and not response.content.at_eof():
                # Feed the parser the next chunk of data.
                parser.feed((await response.content.read(chunk_size)).decode(encoding))
                for event, node in parser.read_events():
                    if event == 'start':
                        if is_content(node):
                            # Content node reached, stop discarding.
                            discard = False
                        continue

                    if is_content(node):
                        # Content node finished, exit.
                        content = node
                        break

                    if discard:
                        # Discard everything before this point.
                        node.clear()
                        for ancestor in node.xpath('ancestor-or-self::*'):
                            while ancestor.getprevious() is not None:
                                del ancestor.getparent()[0]

        #
        # Parse the playlist header.
        #

        pl_header = content[0]
        assert pl_header.get('id') == 'pl-header'

        # Get the thumbnail.
        pl_thumb = pl_header[0][0]
        assert pl_thumb.tag == 'img'
        playlist['thumbnail'] = pl_thumb.get('src')

        # Get the title.
        pl_title = pl_header[1][0]
        assert pl_title.tag == 'h1'
        playlist['title'] = pl_title.text.strip()

        # Get the uploader.
        pl_uploader = pl_header[1][1][0][0]
        assert pl_uploader.tag == 'a'
        playlist['uploader'] = {
            'name': pl_uploader.text,
            'url': 'https://www.youtube.com' + pl_uploader.get('href')
        }

        # Get the length.
        pl_length = pl_header[1][1][1]
        assert pl_length.tag == 'li'
        playlist['length'] = parse_int(pl_length.text, aggressive=True)

        # Get the view count.
        pl_views = pl_header[1][1][2]
        assert pl_views.tag == 'li'
        playlist['views'] = parse_int(pl_views.text, aggressive=True)

        # Get the description.
        pl_description = pl_header[1][2][0]
        assert pl_description.tag == 'span'
        playlist['description'] = pl_description.text.strip()

        #
        # Parse the playlist items.
        #

        def parse_item(node):
            item = {'id': node.get('data-video-id')}

            # Get the video thumbnail.
            vid_thumb = node[2][0][0][0][0][0][0]
            assert vid_thumb.tag == 'img'
            item['thumbnail'] = vid_thumb.get('data-thumb')

            # Get video title.
            vid_title = node[3][0]
            assert vid_title.tag == 'a'
            item['title'] = vid_title.text.strip()

            # Get video uploader.
            vid_uploader = node[3][1][0]
            assert vid_uploader.tag == 'a'
            item['uploader'] = {
                'name': vid_uploader.text,
                'url': 'https://www.youtube.com' + vid_uploader.get('href')
            }

            # Get video length.
            vid_length = node[6][0][0][0]
            assert vid_length.tag == 'span'
            item['lengthSeconds'] = parse_ts(vid_length.text)

            return item

        pl_items = content[1][0][0][0][0]
        assert pl_items.get('id') == 'pl-load-more-destination'

        playlist['items'] += map(parse_item, pl_items)

        #
        # Fetch and parse all continuations.
        #

        load_more = index_s(content, 1, 0, 0, 1)
        assert load_more.tag == 'button'
        load_more = load_more.get('data-uix-load-more-href') if load_more is not None else None
        while load_more is not None:
            # Request the continuation contents.
            async with session.get(
                'https://www.youtube.com' + load_more,
                headers={'Accept': 'application/json'}
            ) as response:
                # Assert that this really worked the way we wanted.
                assert response.status == 200
                assert response.content_type == 'application/json'
                encoding = response.get_encoding()
                assert is_valid_encoding(encoding)

                # Parse the result data (large!)
                # TODO: This ought to be streamed as well.
                data = await response.json()
                assert 'content_html' in data
                assert 'load_more_widget_html' in data

                # Parse all new items.
                parser = etree.HTMLPullParser(events=('end',))
                parser.feed(data['content_html'])
                for _, node in parser.read_events():
                    if node.tag == 'tr':
                        playlist['items'] += [parse_item(node)]

                        # Discard everything before this point.
                        node.clear()
                        for ancestor in node.xpath('ancestor-or-self::*'):
                            while ancestor.getprevious() is not None:
                                del ancestor.getparent()[0]

                # Extract the next continuation link
                match = re.search(
                    r'data-uix-load-more-href=\"(.+?)\"',
                    data['load_more_widget_html']
                )
                if match:
                    # Next continuation link.
                    load_more = match.group(1)
                else:
                    # No more continuations.
                    load_more = None

    return playlist

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

    cli = ArgumentParser(description='Fetch YoutTube playlist metadata')
    cli.add_argument(
        'playlistId',
        metavar='ID',
        nargs='+',
        help='playlist id'
    )
    cli.add_argument(
        '--output',
        nargs='?',
        default='list_{id}.json',
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
        for id in tqdm(args.playlistId, file=sys.stderr):
            with open_output(id) as file:
                try:
                    dump(run_sync(fetch_playlist, id, args.chunk_size), file)
                except Exception as e:
                    print("\nError fetching playlist:", file=sys.stderr)
                    print(e, file=sys.stderr)

        sys.exit(0)
    except Exception as e:
        print("\nUnexpected error:", file=sys.stderr)
        print(e, file=sys.stderr)
        sys.exit(1)