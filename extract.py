from mutagen.id3 import ID3, APIC
from PIL import Image
import numpy as np


def extract_album_art(mp3_path, output_image_path="cover.jpg"):
    audio = ID3(mp3_path)

    for tag in audio.values():
        if isinstance(tag, APIC):
            with open(output_image_path, 'wb') as img:
                img.write(tag.data)
            print(f"Album art saved to: {output_image_path}")
            return output_image_path

    print("No album art found.")
    return None


def crop_black_bars(image_path, output_path="cropped_cover.jpg"):
    image = Image.open(image_path).convert("RGB")
    np_image = np.array(image)

    gray = np.mean(np_image, axis=2)
    threshold = 10
    cols = np.where(np.mean(gray, axis=0) > threshold)[0]

    if cols.size == 0:
        print("No non-black region found.")
        return None

    left, right = cols[0], cols[-1] + 1

    cropped = image.crop((left, 0, right, image.height))
    cropped.save(output_path)
    print(f"Cropped image saved to: {output_path}")
    return output_path


crop_black_bars("cover.jpg", output_path="thumbnails/Yvette.jpg")
extract_album_art("playlists/strinova/Yvette's Theme.mp3")
