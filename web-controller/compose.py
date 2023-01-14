import glob
from PIL import Image
from minio import Minio
import os
from celery import Celery
import shutil
import string
import random

BROKER_URL = os.environ.get("CELERY_BROKER_URL",
                            "redis://localhost:6378/0"),
RES_BACKEND = os.environ.get("CELERY_RESULT_BACKEND",
                             "db+postgresql://postgres:dbc@localhost:5434/celery")

celery_app = Celery('compose', broker=BROKER_URL,
                    backend=RES_BACKEND)

LOCAL_FILE_PATH = os.environ.get('LOCAL_FILE_PATH')
ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY')
SECRET_KEY = os.environ.get('MINIO_SECRET_KEY')

# MINIO_API_HOST = "http://localhost:9000"
MINIO_URL = os.environ.get("MINIO_URL")

MINIO_CLIENT = Minio(MINIO_URL, access_key=ACCESS_KEY, secret_key=SECRET_KEY, secure=False)
# MINIO_CLIENT = Minio("localhost:9000", access_key=ACCESS_KEY, secret_key=SECRET_KEY, secure=False)

# generate bucket of GIF
found = MINIO_CLIENT.bucket_exists("gif")
if not found:
    MINIO_CLIENT.make_bucket("gif")


@celery_app.task
def to_gif(bucket_name):
    # self.update_state(state='STARTED')

    frames = MINIO_CLIENT.list_objects(bucket_name=bucket_name, prefix="frame")

    # https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#gif

    os.mkdir(bucket_name)
    for obj in frames:
        fp = bucket_name + "/" + obj.object_name
        MINIO_CLIENT.fget_object(bucket_name=bucket_name, object_name=obj.object_name, file_path=fp)

    frames = bucket_name + "/frame*.png"

    imgs = (Image.open(f) for f in sorted(glob.glob(frames)))
    img = next(imgs)  # extract first image from iterator

    s = 10
    fp_out = ''.join(random.choices(string.ascii_lowercase + string.digits, k=s)) + '.gif'

    img.save(fp=fp_out, format='GIF', append_images=imgs,
             save_all=True, duration=1 / 15, loop=0)

    MINIO_CLIENT.fput_object(bucket_name="gif", object_name=fp_out, file_path="./" + fp_out, content_type="image/gif")

    os.remove(fp_out)
    shutil.rmtree(bucket_name)

    return "Video Thumbnail Created!!!"

