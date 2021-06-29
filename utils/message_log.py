import requests
import mimetypes
import os

async def download_file(url: str, filename: str, save_path: str):
    # asynchronous file download utility
    response = requests.get(url, allow_redirects=True)
    if response.status_code != 200:
        return
    
    try:
        os.mkdir("./attachments")
    except:
        pass
    
    # attempting to guess the file extension from the MIME type
    file_extension = mimetypes.guess_extension(response.headers.get('content-type'))
    if file_extension is not None:
        filename = filename+file_extension
    
    # attempting to write, in case of failure or if file exists, it is closed automatically.
    try:
        file = open(f'{save_path}/{filename}', 'wb')
        file.write(response.content)
    finally:
        file.close()