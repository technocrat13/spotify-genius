from flask import Flask, render_template, request, session
import json
import boto3
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

app = Flask(__name__)
app.secret_key = 'yoursecretkey'  # Replace with your secret key

cid ='c73aee93e62c4b4aadb40c746b1abdc4'
secret ='14ce72b007bb4d24a40952c21f3b32e7'

client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret)
sp = spotipy.Spotify(client_credentials_manager = client_credentials_manager)

s3_client = boto3.client('s3', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')

def reco_info(reco_list):
    # This is just an example. In your actual app, you would get the reco_list from your recommender system.
    # reco_list = ['5CQ30WqJwcep0pYcV4AMNc', '2x0RZdkZcD8QRI53XT4GI5', '4VqPOruhp5EdPBeR92t6lQ']

    # Get track details from Spotify
    tracks = sp.tracks(reco_list)

    # Extract the necessary details and store them in a list
    reco_tracks = []
    for track in tracks['tracks']:
        reco_tracks.append({
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'album': track['album']['name'],
            'image_url': track['album']['images'][0]['url'],
            'track_url': track['external_urls']['spotify']
        })
    return reco_tracks



@app.route('/', methods=['GET', 'POST'])
def index():
    session.clear()
    if request.method == 'POST':
        playlist_url = request.form['playlist_url']
        playlist = sp.playlist(playlist_url)
        playlist_name = playlist['name']
        playlist_description = playlist['description']
        session['playlist_name'] = playlist_name
        session['playlist_description'] = playlist_description
        playlist_image_url = playlist['images'][0]['url']
        session['playlist_image_url'] = playlist_image_url


        results = sp.playlist_tracks(playlist_url)

        # Batch songs and send to Lambda function
        batch = []
        song_list = []
        for item in results['items']:
            track = item['track']
            track_id = track['id']
            track_name = track['name']
            artist_name = track['artists'][0]['name']

            song_list.append(f"{track_name} by {artist_name}")

            # Check if the song is already in the S3 bucket
            response = s3_client.list_objects_v2(Bucket='spotify-genius-featurestore', Prefix=f'processed-features/{track_id}_{track_name}_{artist_name}')
            if 'Contents' in response:
                print(f"Track {track_name} is already in the S3 bucket.")
                continue

            batch.append({
                'id': track_id,
                'name': track_name,
                'artist': artist_name,
                'popularity': track['popularity'],
                'explicit': int(track['explicit']),
            })
            if len(batch) == 25:
                lambda_client.invoke(
                    FunctionName='lambda-lyrics-getter',
                    InvocationType='Event',
                    Payload=json.dumps(batch),
                )
                batch = []
        if len(batch) > 0:
            lambda_client.invoke(
                FunctionName='lambda-lyrics-getter',
                InvocationType='Event',
                Payload=json.dumps(batch),
            )

        session['song_list'] = song_list

        # reply front endpoint will be here:

        reco_tracks = ['7eX5SypK35V8Y9d9pS6rWy',
                        '4fPBB44eDH71YohayI4eKV',
                        '2M7UdnD0fEaryh8TnCvqFX',
                        '6LqZFfv4fUP7va14Y6VW9a',
                        ]
        
        reco_tracks = reco_info(reco_tracks)

        return render_template('index.html', playlist_name=playlist_name, playlist_description=playlist_description, song_list=song_list, reco_tracks=reco_tracks)
    else:
        playlist_name = session.get('playlist_name')
        playlist_description = session.get('playlist_description')
        song_list = session.get('song_list')
        # reco_tracks = ['7eX5SypK35V8Y9d9pS6rWy',
        #                 '4fPBB44eDH71YohayI4eKV',
        #                 '2M7UdnD0fEaryh8TnCvqFX',
        #                 '6LqZFfv4fUP7va14Y6VW9a',
        #                 ]
        # reco_tracks = reco_info(reco_tracks)

    return render_template('index.html', playlist_name=playlist_name, playlist_description=playlist_description, song_list=song_list)

if __name__ == '__main__':
    app.run(debug=True)