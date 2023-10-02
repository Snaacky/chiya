from pathlib import Path
import inspect

from chiya import config

def get_image(imgname: str) -> str:
    """
    Takes the name of the image and grabs the filename of the function using the inspect module.
        Args: 
            imgname: The name of the image file, including the file extension.
        Returns: 
            The URL of the image file.
    """
    base_url = config["lfs_url"]
    full_path = inspect.stack()[1].filename
    filename = Path(full_path).stem 
    image_url = f"{base_url}/{filename}/{imgname}"
    return image_url
