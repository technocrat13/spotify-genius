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

@app.route('/', methods=['GET', 'POST'])
def index():
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
                    FunctionName='spotify-lyrcis-getter-3',
                    InvocationType='Event',
                    Payload=json.dumps(batch),
                )
                batch = []
        if len(batch) > 0:
            lambda_client.invoke(
                FunctionName='spotify-lyrcis-getter-3',
                InvocationType='Event',
                Payload=json.dumps(batch),
            )

        session['song_list'] = song_list

        return render_template('index.html', playlist_name=playlist_name, playlist_description=playlist_description, song_list=song_list)
    else:
        playlist_name = session.get('playlist_name')
        playlist_description = session.get('playlist_description')
        song_list = session.get('song_list')

    return render_template('index.html', playlist_name=playlist_name, playlist_description=playlist_description, song_list=song_list)

if __name__ == '__main__':
    app.run(debug=True)