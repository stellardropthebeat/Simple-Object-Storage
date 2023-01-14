import cv2
import imutils
import sys
import string
import random
import os
from minio import Minio

from celery import Celery
import compose

# BROKER_URL = "redis://localhost:6378"
# RES_BACKEND = "db+postgresql://postgres:dbc@localhost:5434/celery"

BROKER_URL = os.environ.get("CELERY_BROKER_URL",
                            "redis://localhost:6378/0"),
RES_BACKEND = os.environ.get("CELERY_RESULT_BACKEND",
                             "db+postgresql://postgres:dbc@localhost:5434/celery")

celery_app = Celery('extract', broker=BROKER_URL,
                    backend=RES_BACKEND)

LOCAL_FILE_PATH = os.environ.get('LOCAL_FILE_PATH')
ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY')
SECRET_KEY = os.environ.get('MINIO_SECRET_KEY')

# MINIO_API_HOST = "http://localhost:9000"
MINIO_URL = os.environ.get("MINIO_URL")

MINIO_CLIENT = Minio(MINIO_URL, access_key=ACCESS_KEY, secret_key=SECRET_KEY, secure=False)
# MINIO_CLIENT = Minio("localhost:9000", access_key=ACCESS_KEY, secret_key=SECRET_KEY, secure=False)

# generate bucket of videos
found = MINIO_CLIENT.bucket_exists("videos")
if not found:
    MINIO_CLIENT.make_bucket("videos")


@celery_app.task
def get_frames(video, bucket):
    # self.update_state(state='STARTED')

    # generate bucket of frames extracted
    s = 10  # number of characters in the string.
    randstr = ''.join(random.choices(string.ascii_lowercase + string.digits, k=s))
    found = MINIO_CLIENT.bucket_exists(randstr)
    if not found:
        MINIO_CLIENT.make_bucket(randstr)
    else:
        print("Bucket already exists")

    MINIO_CLIENT.fget_object(bucket_name=bucket, object_name=video, file_path=video)

    if not os.path.exists("images"):
        os.mkdir("images")

    vidcap = cv2.VideoCapture(video)
    # fps = vidcap.get(cv2.CAP_PROP_FPS)
    length = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
    success, image = vidcap.read()
    count = 0

    while success:
        if 1 / 3 * length < count < 1 / 3 * length + 15 * 15:
            frame = imutils.resize(image, width=360)
            cv2.imwrite("images/frame%d.png" % count, frame)
            MINIO_CLIENT.fput_object(randstr, object_name="frame%d.png" % count,
                                     file_path="images/frame%d.png" % count, content_type="image/png")
            try:
                os.remove("images/frame%d.png" % count)
            except:
                pass
        success, image = vidcap.read()
        count += 1


    print("Successfully uploaded all frames to bucket")

    task = compose.celery_app.send_task('compose.to_gif', queue='q02', kwargs={'bucket_name': randstr})

    return task.task_id


if __name__ == '__main__':
    fp_in = sys.argv[1]
    get_frames(fp_in)
